"""
Command builders for the X-NUCLEO-LPM01A PowerShield.

All commands are newline-terminated ASCII strings.
Responses begin with 'ack' (success) or 'err' (failure).
"""


class Commands:
    """Builds command byte strings for the PowerShield device."""

    BAUD_RATE = 3686400

    # Valid sampling frequencies in Hz
    FREQ_OPTIONS = [
        (100000, "100 kHz"), (50000, "50 kHz"), (20000, "20 kHz"),
        (10000, "10 kHz"), (5000, "5 kHz"), (2000, "2 kHz"),
        (1000, "1 kHz"), (500, "500 Hz"), (200, "200 Hz"),
        (100, "100 Hz"), (50, "50 Hz"), (20, "20 Hz"),
        (10, "10 Hz"), (5, "5 Hz"), (2, "2 Hz"), (1, "1 Hz"),
    ]

    @staticmethod
    def _enc(s: str) -> bytes:
        return (s + "\n").encode("ascii")

    # ── Common commands ────────────────────────────────────────────────────────
    @classmethod
    def help(cls) -> bytes:
        return cls._enc("help")

    @classmethod
    def echo(cls, text: str) -> bytes:
        return cls._enc(f"echo {text}")

    @classmethod
    def powershield(cls) -> bytes:
        return cls._enc("powershield")

    @classmethod
    def version(cls) -> bytes:
        return cls._enc("version")

    @classmethod
    def status(cls) -> bytes:
        return cls._enc("status")

    @classmethod
    def htc(cls) -> bytes:
        """Host takes control (standalone → host mode)."""
        return cls._enc("htc")

    @classmethod
    def hrc(cls) -> bytes:
        """Host releases control (host mode → standalone)."""
        return cls._enc("hrc")

    @classmethod
    def lcd(cls, line: int, text: str) -> bytes:
        """Display text on LCD (line 1 or 2, max 16 chars)."""
        return cls._enc(f'lcd {line} "{text[:16]}"')

    @classmethod
    def psrst(cls) -> bytes:
        """Hardware reset of the PowerShield."""
        return cls._enc("psrst")

    # ── Measurement configuration ──────────────────────────────────────────────
    @classmethod
    def volt(cls, mv: int) -> bytes:
        """Set supply voltage in millivolts (1800–3300 mV)."""
        return cls._enc(f"volt {mv}m")

    @classmethod
    def volt_get(cls) -> bytes:
        return cls._enc("volt get")

    @classmethod
    def freq(cls, hz: int) -> bytes:
        """Set sampling frequency in Hz."""
        if hz >= 1000:
            return cls._enc(f"freq {hz // 1000}k")
        return cls._enc(f"freq {hz}")

    @classmethod
    def acqtime(cls, seconds: float) -> bytes:
        """Set acquisition time in seconds (0 = power-down target)."""
        if seconds <= 0:
            return cls._enc("acqtime 0")
        ms = int(round(seconds * 1000))
        if ms < 1000:
            return cls._enc(f"acqtime {ms}m")
        return cls._enc(f"acqtime {int(seconds)}")

    @classmethod
    def acqtime_inf(cls) -> bytes:
        """Set infinite acquisition duration."""
        return cls._enc("acqtime inf")

    @classmethod
    def acqmode(cls, mode: str) -> bytes:
        """Set acquisition mode: 'dyn' or 'stat'."""
        return cls._enc(f"acqmode {mode}")

    @classmethod
    def funcmode(cls, mode: str) -> bytes:
        """Set function mode: 'optim' or 'high'."""
        return cls._enc(f"funcmode {mode}")

    @classmethod
    def output(cls, out: str) -> bytes:
        """Set output type: 'current' or 'energy'."""
        return cls._enc(f"output {out}")

    @classmethod
    def format_cmd(cls, fmt: str) -> bytes:
        """Set data format: 'ascii_dec' or 'bin_hexa'."""
        return cls._enc(f"format {fmt}")

    @classmethod
    def trigsrc(cls, src: str) -> bytes:
        """Set trigger source: 'sw' or 'd7'."""
        return cls._enc(f"trigsrc {src}")

    @classmethod
    def trigdelay(cls, ms: int) -> bytes:
        """Set trigger delay in milliseconds (0–30000 ms)."""
        if ms == 0:
            return cls._enc("trigdelay 0")
        return cls._enc(f"trigdelay {ms}m")

    @classmethod
    def currthre(cls, ma: float) -> bytes:
        """Set current threshold in milliamps (0–10 mA).

        Sends the value as integer microamps with the 'u' suffix (no space)
        to avoid decimal literals and whitespace tokenisation issues.
        """
        ua = int(round(ma * 1000))
        return cls._enc(f"currthre {ua}u")

    @classmethod
    def pwr(cls, state: str) -> bytes:
        """Set power state: 'auto', 'on', 'off', or 'get'."""
        return cls._enc(f"pwr {state}")

    @classmethod
    def pwrend(cls, state: str) -> bytes:
        """Set power state after acquisition: 'on' or 'off'."""
        return cls._enc(f"pwrend {state}")

    # ── Acquisition operation ─────────────────────────────────────────────────
    @classmethod
    def start(cls) -> bytes:
        return cls._enc("start")

    @classmethod
    def stop(cls) -> bytes:
        return cls._enc("stop")

    @classmethod
    def targrst(cls, ms: int) -> bytes:
        """Reset target by disconnecting power supply for `ms` milliseconds."""
        if ms == 0:
            return cls._enc("targrst 0")
        return cls._enc(f"targrst {ms}m")

    @classmethod
    def temp(cls, unit: str = "degc") -> bytes:
        """Get board temperature: unit 'degc' or 'degf'."""
        return cls._enc(f"temp {unit}")

    # ── Board state ───────────────────────────────────────────────────────────
    @classmethod
    def autotest(cls, arg: str = "start") -> bytes:
        """Run board autotest ('start' or 'status')."""
        return cls._enc(f"autotest {arg}")

    @classmethod
    def calib(cls) -> bytes:
        """Perform board self-calibration."""
        return cls._enc("calib")
