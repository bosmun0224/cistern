"""Unit tests for the v1.15.0 hang-recovery changes.

Covers the two mechanisms that keep the device from wedging silently:
  1. Every urequests call carries a socket timeout (firebase.py / ota.py),
     with a safe fallback if urequests is too old to accept the kwarg.
  2. uptime_s() stays monotonic across the ticks_ms() wrap at 2**30 ms.

These run on CPython, so MicroPython-only modules are stubbed.
"""

import subprocess
import sys
import textwrap
import types
import unittest


def _install_stubs():
    """Stub MicroPython-only modules needed to import firebase.py / ota.py."""
    if "urequests" not in sys.modules:
        sys.modules["urequests"] = types.ModuleType("urequests")
    if "machine" not in sys.modules:
        machine = types.ModuleType("machine")
        machine.reset = lambda: None
        sys.modules["machine"] = machine


_install_stubs()

import firebase  # noqa: E402
import ota  # noqa: E402


class _RecordingRequests:
    """Stands in for urequests, recording how each call was made."""

    def __init__(self, accepts_timeout=True):
        self.accepts_timeout = accepts_timeout
        self.calls = []

    def _handle(self, kind, kwargs):
        if "timeout" in kwargs and not self.accepts_timeout:
            # Mirrors CPython/MicroPython argument binding: TypeError is raised
            # before the function body runs, so no request is ever sent.
            raise TypeError("unexpected keyword argument 'timeout'")
        self.calls.append((kind, kwargs.get("timeout")))
        return object()

    def post(self, url, **kwargs):
        return self._handle("post", kwargs)

    def get(self, url, **kwargs):
        return self._handle("get", kwargs)


class TestFirebaseTimeout(unittest.TestCase):
    """firebase._post must always bound the socket read."""

    def setUp(self):
        self._real = firebase.urequests
        firebase._timeout_supported = True

    def tearDown(self):
        firebase.urequests = self._real
        firebase._timeout_supported = True

    def test_post_passes_timeout(self):
        fake = _RecordingRequests()
        firebase.urequests = fake
        firebase._post("http://x", "{}")
        self.assertEqual(fake.calls, [("post", firebase.REQUEST_TIMEOUT)])

    def test_timeout_is_positive_and_under_watchdog_window(self):
        """Must fire before the 8s hardware watchdog so posts buffer instead
        of tripping a reboot."""
        self.assertGreater(firebase.REQUEST_TIMEOUT, 0)
        self.assertLess(firebase.REQUEST_TIMEOUT, 8)

    def test_falls_back_when_timeout_unsupported(self):
        fake = _RecordingRequests(accepts_timeout=False)
        firebase.urequests = fake
        firebase._post("http://x", "{}")
        # Exactly one request reached the network — the TypeError attempt
        # never sent anything, so the reading is not double-posted.
        self.assertEqual(fake.calls, [("post", None)])

    def test_fallback_is_sticky(self):
        """After one TypeError we stop retrying with the kwarg."""
        fake = _RecordingRequests(accepts_timeout=False)
        firebase.urequests = fake
        firebase._post("http://x", "{}")
        firebase._post("http://x", "{}")
        self.assertFalse(firebase._timeout_supported)
        self.assertEqual(fake.calls, [("post", None), ("post", None)])


class TestOtaTimeout(unittest.TestCase):
    """ota._get must bound downloads the same way."""

    def setUp(self):
        self._real = ota.urequests
        ota._timeout_supported = True

    def tearDown(self):
        ota.urequests = self._real
        ota._timeout_supported = True

    def test_get_passes_timeout(self):
        fake = _RecordingRequests()
        ota.urequests = fake
        ota._get("http://x")
        self.assertEqual(fake.calls, [("get", ota.REQUEST_TIMEOUT)])

    def test_falls_back_when_timeout_unsupported(self):
        fake = _RecordingRequests(accepts_timeout=False)
        ota.urequests = fake
        ota._get("http://x")
        self.assertEqual(fake.calls, [("get", None)])

    def test_timeout_under_watchdog_window(self):
        self.assertGreater(ota.REQUEST_TIMEOUT, 0)
        self.assertLess(ota.REQUEST_TIMEOUT, 8)


# main.py installs a module-level Pin('LED') and pulls in sensor/ota/firebase,
# and it needs time.ticks_* which CPython lacks. Rather than patch the shared
# `time` module for the whole test process, exercise uptime_s() in a subprocess
# with a fully controlled fake clock.
_UPTIME_HARNESS = textwrap.dedent(
    '''
    import sys, types, time

    PERIOD = 1 << 30          # MicroPython ticks_ms() wraps at 2**30
    HALF = PERIOD >> 1
    clock = {"now": 0}

    time.ticks_ms = lambda: clock["now"] % PERIOD
    def _diff(a, b):
        d = (a - b) % PERIOD
        return d - PERIOD if d >= HALF else d
    time.ticks_diff = _diff
    time.ticks_add = lambda t, delta: (t + delta) % PERIOD

    machine = types.ModuleType("machine")
    class Pin:
        OUT = 1
        IN = 0
        PULL_UP = 2
        def __init__(self, *a, **kw): pass
        def on(self): pass
        def off(self): pass
        def value(self, *a): return 1     # GP15 high = debug jumper absent
    machine.Pin = Pin
    machine.ADC = lambda *a, **kw: types.SimpleNamespace(read_u16=lambda: 0)
    machine.reset = lambda: None
    machine.reset_cause = lambda: 1
    machine.I2C = lambda *a, **kw: types.SimpleNamespace(
        scan=lambda: [], readfrom_mem=lambda *a: b"\\x00\\x00",
        writeto_mem=lambda *a: None, writeto=lambda *a: None)
    machine.WDT = lambda **kw: types.SimpleNamespace(feed=lambda: None)
    sys.modules["machine"] = machine
    sys.modules["urequests"] = types.ModuleType("urequests")
    sys.modules["network"] = types.ModuleType("network")

    import main

    STEP_MS = 60_000
    steps = 40 * 24 * 60          # 40 days at one call per minute
    for _ in range(steps):
        clock["now"] += STEP_MS
        value = main.uptime_s()

    expected = steps * STEP_MS // 1000
    naive = (clock["now"] % PERIOD) // 1000
    print(value, expected, naive)
    '''
)


class TestUptimeWrap(unittest.TestCase):
    """uptime_s() must survive the ~12.4 day ticks_ms() rollover."""

    def _run(self):
        proc = subprocess.run(
            [sys.executable, "-c", _UPTIME_HARNESS],
            capture_output=True, text=True, cwd=".",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        got, expected, naive = (int(x) for x in proc.stdout.split())
        return got, expected, naive

    def test_monotonic_across_wraps(self):
        got, expected, _ = self._run()
        self.assertEqual(got, expected)

    def test_beats_the_naive_implementation(self):
        """Guards against reverting to time.ticks_ms() // 1000."""
        got, expected, naive = self._run()
        self.assertNotEqual(naive, expected)
        self.assertGreater(got, naive)


if __name__ == "__main__":
    unittest.main()
