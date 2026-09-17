import unittest

from qcodes_contrib_drivers.drivers.QuTech.S4c import S4c


class TestS4c(unittest.TestCase):
    def test_total_gain_voltage_mode_is_one(self):
        s4c = S4c('test_s4c_v')
        try:
            s4c.source_mode('V')
            self.assertEqual(s4c.total_gain(), 1.0)
            s4c.source_mode('V+R')
            self.assertEqual(s4c.total_gain(), 1.0)
        finally:
            s4c.close()

    def test_total_gain_current_mode_maps_range_to_amps(self):
        s4c = S4c('test_s4c_i')
        try:
            s4c.source_mode('I')
            s4c.range('1m')
            self.assertEqual(s4c.total_gain(), 1e-3)
            s4c.range('20m')
            self.assertEqual(s4c.total_gain(), 20e-3)
        finally:
            s4c.close()
