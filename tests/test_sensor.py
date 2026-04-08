"""Unit tests for sensor.py raw-read logic and dashboard computation.

sensor.py now returns only raw ADC + voltage. All depth/gallons computation
is done client-side on the dashboard.  These tests verify:
  1. The MicroPython sensor module can be imported and returns expected keys.
  2. The dashboard computation (replicated here in pure Python) is correct.
"""

import math
import sys
import types
import unittest

# Stub out MicroPython-only modules so sensor.py can be imported on CPython.
_machine = types.ModuleType("machine")
_machine.I2C = lambda *a, **kw: type(
    "I2C", (),
    {
        "scan": lambda s: [],
        "readfrom_mem": lambda *a: b"\x00\x00",
        "writeto_mem": lambda *a: None,
    },
)()
_machine.Pin = lambda *a, **kw: None
sys.modules["machine"] = _machine

from sensor import read_voltage  # noqa: E402

# ---- Dashboard computation replicated in Python ----
V_MIN = 0.66
V_MAX = 3.3
DEPTH_MAX_M = 5.0
M_TO_IN = 39.3701
TANK_RADIUS_IN = 28.8
TANK_DIAMETER_IN = TANK_RADIUS_IN * 2
TANK_LENGTH_IN = 133.0
TANK_MAX_GAL = 1500


def voltage_to_depth(voltage):
    v = max(V_MIN, min(V_MAX, voltage))
    depth_m = ((v - V_MIN) / (V_MAX - V_MIN)) * DEPTH_MAX_M
    depth_in = depth_m * M_TO_IN
    return depth_m, depth_in


def depth_to_gallons(depth_in):
    R = TANK_RADIUS_IN
    h = max(0, min(TANK_DIAMETER_IN, depth_in))
    if h <= 0:
        return 0.0
    if h >= TANK_DIAMETER_IN:
        return TANK_MAX_GAL
    area = R * R * math.acos((R - h) / R) - (R - h) * math.sqrt(2 * R * h - h * h)
    return (area * TANK_LENGTH_IN) / 231.0


class TestReadSensor(unittest.TestCase):
    """Verify sensor.read_voltage returns the expected shape."""

    def test_read_voltage_returns_tuple(self):
        raw, voltage = read_voltage(0)
        self.assertIsInstance(raw, int)
        self.assertIsInstance(voltage, float)


class TestDashboardDepthConversion(unittest.TestCase):
    """Test the voltage → depth conversion that runs on the dashboard."""

    def test_min_voltage_gives_zero_depth(self):
        depth_m, depth_in = voltage_to_depth(V_MIN)
        self.assertEqual(depth_m, 0.0)
        self.assertEqual(depth_in, 0.0)

    def test_max_voltage_gives_full_depth(self):
        depth_m, _ = voltage_to_depth(V_MAX)
        self.assertEqual(depth_m, DEPTH_MAX_M)

    def test_midpoint_voltage(self):
        mid_v = (V_MIN + V_MAX) / 2
        depth_m, _ = voltage_to_depth(mid_v)
        self.assertAlmostEqual(depth_m, DEPTH_MAX_M / 2, places=2)

    def test_below_min_clamps_to_zero(self):
        depth_m, _ = voltage_to_depth(0.0)
        self.assertEqual(depth_m, 0.0)

    def test_above_max_clamps_to_full(self):
        depth_m, _ = voltage_to_depth(5.0)
        self.assertEqual(depth_m, DEPTH_MAX_M)

    def test_negative_voltage_clamps(self):
        depth_m, _ = voltage_to_depth(-1.0)
        self.assertEqual(depth_m, 0.0)


class TestDashboardGallonsConversion(unittest.TestCase):
    """Test the horizontal-cylinder depth → gallons conversion."""

    def test_zero_depth_gives_zero_gallons(self):
        self.assertEqual(depth_to_gallons(0), 0.0)

    def test_full_depth_gives_max_gallons(self):
        self.assertEqual(depth_to_gallons(TANK_DIAMETER_IN), TANK_MAX_GAL)

    def test_negative_depth_gives_zero(self):
        self.assertEqual(depth_to_gallons(-1.0), 0.0)

    def test_overflow_depth_gives_max(self):
        self.assertEqual(depth_to_gallons(999), TANK_MAX_GAL)

    def test_half_depth_gives_half_volume(self):
        """At the radius (half diameter), volume should be exactly half."""
        gallons = depth_to_gallons(TANK_RADIUS_IN)
        self.assertAlmostEqual(gallons, TANK_MAX_GAL / 2, delta=50)

    def test_bottom_fills_slowly(self):
        """First inch should yield very few gallons."""
        self.assertLess(depth_to_gallons(1.0), 20)

    def test_middle_fills_fastest(self):
        """Gallons per inch should be highest around the middle."""
        low = depth_to_gallons(10) - depth_to_gallons(5)
        mid = depth_to_gallons(TANK_RADIUS_IN + 2.5) - depth_to_gallons(TANK_RADIUS_IN - 2.5)
        self.assertGreater(mid, low)


if __name__ == "__main__":
    unittest.main()
