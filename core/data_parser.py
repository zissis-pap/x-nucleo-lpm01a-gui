"""
Data stream parsers for X-NUCLEO-LPM01A PowerShield.

Two formats are supported:
  ascii_dec  – ASCII decimal, up to 10 kHz, 9 bytes/sample (DDDDSZZ\\r\\n)
  bin_hexa   – Binary hex,   up to 100 kHz, 2 bytes/sample

In both formats the device injects metadata (timestamps, errors, end-of-
acquisition markers) into the data stream.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Shared result container
# ---------------------------------------------------------------------------

@dataclass
class ParsedData:
    """Holds all parsed output from one chunk of raw serial data."""

    samples: List[float] = field(default_factory=list)
    """Current / energy values in Amperes (or Joules for energy output)."""

    ack_lines: List[Tuple[bool, str, str]] = field(default_factory=list)
    """(success, command_name, payload) for every ack/err line."""

    errors: List[str] = field(default_factory=list)
    """Error messages embedded in the data stream."""

    timestamps: List[Tuple[int, int]] = field(default_factory=list)
    """(time_ms, buffer_percent) from every timestamp metadata record."""

    end_of_acquisition: bool = False
    overcurrent: bool = False

    raw_lines: List[str] = field(default_factory=list)
    """Every decoded text line, for the console log."""


# ---------------------------------------------------------------------------
# ASCII decimal parser
# ---------------------------------------------------------------------------

class AsciiParser:
    """
    Parses the ASCII decimal data stream.

    Each measurement sample is 7 printable characters + \\r\\n::

        6409-07\\r\\n  →  6409 × 10^(−7) = 640.9 µA

    Measurement lines begin with a digit.
    All other lines are metadata (ack, err, Timestamp, end, error, …).
    """

    def __init__(self) -> None:
        self._buf = ""

    def reset(self) -> None:
        self._buf = ""

    def feed(self, text: str) -> ParsedData:
        result = ParsedData()
        self._buf += text

        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            line = line.rstrip("\r")
            if not line:
                continue
            result.raw_lines.append(line)
            self._dispatch(line, result)

        return result

    # ------------------------------------------------------------------
    def _dispatch(self, line: str, result: ParsedData) -> None:
        ch = line[0]

        if ch.isdigit():
            # Measurement sample
            val = self._parse_sample(line)
            if val is not None:
                result.samples.append(val)

        elif line.startswith("ack "):
            parts = line[4:].strip().split(None, 1)
            cmd = parts[0] if parts else ""
            data = parts[1] if len(parts) > 1 else ""
            result.ack_lines.append((True, cmd, data))

        elif line.startswith("err "):
            result.ack_lines.append((False, line[4:].strip(), ""))

        elif line == "end":
            result.end_of_acquisition = True

        elif line.startswith("error"):
            result.errors.append(line[5:].strip())

        elif "Timestamp" in line or "timestamp" in line:
            ts = self._parse_timestamp(line)
            if ts:
                result.timestamps.append(ts)

        # summary begin / summary end / pwr on / pwr off → ignore silently

    # ------------------------------------------------------------------
    @staticmethod
    def _parse_sample(line: str) -> Optional[float]:
        """Parse 'DDDDSZZ' → float in Amperes."""
        try:
            if len(line) < 7:
                return None
            mantissa = int(line[0:4])
            sign = -1 if line[4] == "-" else 1
            exponent = int(line[5:7])
            return mantissa * (10.0 ** (sign * exponent))
        except (ValueError, IndexError):
            return None

    @staticmethod
    def _parse_timestamp(line: str) -> Optional[Tuple[int, int]]:
        """Return (time_ms, buffer_pct) from a Timestamp metadata line."""
        try:
            time_ms = 0
            sec_m = re.search(r"(\d+)\s*s\b", line)
            ms_m = re.search(r"(\d+)\s*ms", line)
            if sec_m:
                time_ms += int(sec_m.group(1)) * 1000
            if ms_m:
                time_ms += int(ms_m.group(1))
            buf_m = re.search(r"(\d+)\s*%", line)
            buf_pct = int(buf_m.group(1)) if buf_m else 0
            return (time_ms, buf_pct)
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Binary hexadecimal parser
# ---------------------------------------------------------------------------

class BinaryParser:
    """
    Parses the binary hexadecimal data stream.

    Each measurement sample = 2 bytes::

        Byte 1: [neg_pow16(3:0)][value(11:8)]
        Byte 2: [value(7:0)]
        current = value_int / 16^neg_pow16   (Amperes)

    Metadata packets begin with 0xF0 followed by a type byte (0xF1–0xF7)
    and end with 0xFF 0xFF.  neg_pow16 = 0x0F is reserved for metadata
    so no regular sample can start with 0xFx.

    Metadata types
    --------------
    0xF1  Error message  (variable length ASCII + 0xFF 0xFF)
    0xF2  Info message   (variable length ASCII + 0xFF 0xFF)
    0xF3  Timestamp      (4-byte ms, 1-byte buf%, 0xFF 0xFF)
    0xF4  End of acquisition (0xFF 0xFF)
    0xF5  Overcurrent    (0xFF 0xFF)
    0xF6  Target power down (0xFF 0xFF)
    0xF7  Voltage        (2-byte mV, 0xFF 0xFF)
    """

    def __init__(self) -> None:
        self._buf = bytearray()

    def reset(self) -> None:
        self._buf = bytearray()

    def feed(self, data: bytes) -> ParsedData:
        result = ParsedData()
        self._buf.extend(data)
        pos = 0

        while pos + 1 < len(self._buf):
            b1 = self._buf[pos]
            b2 = self._buf[pos + 1]

            # Metadata: 0xF0 followed by 0xFx
            if b1 == 0xF0 and (b2 & 0xF0) == 0xF0:
                new_pos = self._parse_meta(pos, b2, result)
                if new_pos == pos:
                    break  # Not enough data yet; wait for more
                pos = new_pos
                continue

            # Skip any stray 0xF0 (shouldn't appear alone)
            if (b1 >> 4) == 0x0F:
                pos += 1
                continue

            # Regular 2-byte measurement sample
            neg_pow = (b1 >> 4) & 0x0F
            value_int = ((b1 & 0x0F) << 8) | b2
            if neg_pow > 0:
                current = value_int / (16.0 ** neg_pow)
            else:
                current = float(value_int)
            result.samples.append(current)
            pos += 2

        self._buf = self._buf[pos:]
        return result

    # ------------------------------------------------------------------
    def _parse_meta(self, start: int, meta_type: int, result: ParsedData) -> int:
        """Return new buffer position, or `start` if not enough data."""
        buf = self._buf
        i = start + 2  # skip 0xF0 + type byte

        if meta_type in (0xF1, 0xF2):
            # Variable-length ASCII until 0xFF 0xFF
            for j in range(i, len(buf) - 1):
                if buf[j] == 0xFF and buf[j + 1] == 0xFF:
                    msg = buf[i:j].decode("ascii", errors="replace").strip()
                    if meta_type == 0xF1:
                        result.errors.append(msg)
                    return j + 2
            return start  # incomplete

        if meta_type == 0xF3:
            # 0xF0 0xF3 [4B ms] [1B buf%] 0xFF 0xFF  →  9 bytes total
            if i + 6 > len(buf):
                return start
            time_ms = (
                (buf[i] << 24) | (buf[i + 1] << 16) |
                (buf[i + 2] << 8) | buf[i + 3]
            ) & 0x7FFF_FFFF  # clear overflow bit
            buf_pct = buf[i + 4]
            if buf[i + 5] == 0xFF and buf[i + 6] == 0xFF:
                result.timestamps.append((time_ms, buf_pct))
                return i + 7
            return start

        if meta_type in (0xF4, 0xF5, 0xF6):
            # 0xF0 Fx 0xFF 0xFF  →  4 bytes total
            if i + 1 >= len(buf):
                return start
            if buf[i] == 0xFF and buf[i + 1] == 0xFF:
                if meta_type == 0xF4:
                    result.end_of_acquisition = True
                elif meta_type == 0xF5:
                    result.overcurrent = True
                return i + 2
            return start

        if meta_type == 0xF7:
            # 0xF0 0xF7 [2B mV] 0xFF 0xFF  →  6 bytes total
            if i + 3 >= len(buf):
                return start
            if buf[i + 2] == 0xFF and buf[i + 3] == 0xFF:
                return i + 4
            return start

        # Unknown type: skip 2-byte header
        return start + 2
