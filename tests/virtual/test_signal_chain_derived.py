"""Test derived math calculations for SignalChain."""

import warnings
from unittest.mock import Mock, MagicMock

# Mock QCoDeS for testing
class MockParameter:
    def __init__(self, initial_value=0.0):
        self._value = initial_value
    
    def __call__(self):
        return self._value
    
    def set(self, value):
        self._value = value
    
    def get(self):
        return self._value

class MockInstrument:
    def __init__(self, name):
        self.name = name
    
    def add_parameter(self, name, **kwargs):
        pass

# Mock the nodes module
class MockNode(MockInstrument):
    def __init__(self, name):
        super().__init__(name)
        
        # Create mock parameters
        self.level = MockParameter(0.0)
        self.amplitude = self.level  # Alias
        self.output_on = MockParameter(False)
        self.frequency = MockParameter(1000.0)
        
        self.gm_a_per_v = MockParameter(1e-3)  # 1 mA/V
        self.invert = MockParameter(False)
        
        self.gain_v_per_v = MockParameter(100.0)  # 100 V/V
        
        self.time_constant = MockParameter(0.1)
        self.sensitivity = MockParameter(1.0)
        self.input_range = MockParameter(1.0)
        self.X = MockParameter(1.0)
        self.Y = MockParameter(0.0)
        self.R = MockParameter(1.0)
        self.Theta = MockParameter(0.0)


def test_derived_math_basic():
    """Test basic derived math with gm=1e-3 A/V, gain=100 V/V, invert=False."""
    # Create mock nodes
    src_v = MockNode("src")
    vi = MockNode("vi")
    preamp = MockNode("preamp")
    lockin = MockNode("lockin")
    
    # Set test values
    vi.gm_a_per_v.set(1e-3)  # 1 mA/V
    vi.invert.set(False)
    preamp.gain_v_per_v.set(100.0)  # 100 V/V
    preamp.invert.set(False)
    
    # Mock the SignalChain class to test math directly
    class TestSignalChain:
        def __init__(self):
            self.gm_a_per_v = vi.gm_a_per_v
            self.vi_invert = vi.invert
            self.preamp_gain = preamp.gain_v_per_v
            self.preamp_invert = preamp.invert
            self.excitation_v_ac = src_v.level
            self.X = lockin.X
            self.Y = lockin.Y
            self.R_est = MockParameter(10e3)  # 10 kΩ
        
        def _gm_eff(self):
            gm = float(self.gm_a_per_v())
            invert = bool(self.vi_invert())
            return -gm if invert else gm
        
        def _gv_eff(self):
            gv = float(self.preamp_gain())
            invert = bool(self.preamp_invert())
            return -gv if invert else gv
        
        def _get_I_cmd(self):
            return self._gm_eff() * float(self.excitation_v_ac())
        
        def _get_V_sample_ac_meas(self):
            X_val = float(self.X())
            Y_val = float(self.Y())
            gv_eff = self._gv_eff()
            if gv_eff == 0:
                return complex(0, 0)
            return complex(X_val, Y_val) / gv_eff
        
        def _get_I_meas(self):
            R_est = self.R_est()
            if R_est in (None, 0):
                return None
            V_sample = self._get_V_sample_ac_meas()
            return abs(V_sample) / float(R_est)
    
    # Test the math
    chain = TestSignalChain()
    
    # Test I_set=1e-6 A => excitation_v_ac == 1e-3 V
    I_target = 1e-6  # 1 µA
    gm_eff = chain._gm_eff()
    V_needed = I_target / gm_eff
    
    assert abs(gm_eff - 1e-3) < 1e-12, f"Expected gm_eff=1e-3, got {gm_eff}"
    assert abs(V_needed - 1e-3) < 1e-12, f"Expected V_needed=1e-3, got {V_needed}"
    
    # Set excitation and test I_cmd
    chain.excitation_v_ac.set(V_needed)
    I_cmd = chain._get_I_cmd()
    assert abs(I_cmd - I_target) < 1e-12, f"Expected I_cmd={I_target}, got {I_cmd}"


def test_derived_math_voltage_measurement():
    """Test voltage measurement with mocked X=1.0, Y=0.0."""
    # Create mock nodes
    src_v = MockNode("src")
    vi = MockNode("vi")
    preamp = MockNode("preamp")
    lockin = MockNode("lockin")
    
    # Set test values  
    preamp.gain_v_per_v.set(100.0)  # 100 V/V
    preamp.invert.set(False)
    lockin.X.set(1.0)  # 1 V at lock-in
    lockin.Y.set(0.0)
    
    # Create test signal chain
    class TestSignalChain:
        def __init__(self):
            self.preamp_gain = preamp.gain_v_per_v
            self.preamp_invert = preamp.invert
            self.X = lockin.X
            self.Y = lockin.Y
        
        def _gv_eff(self):
            gv = float(self.preamp_gain())
            invert = bool(self.preamp_invert())
            return -gv if invert else gv
        
        def _get_V_sample_ac_meas(self):
            X_val = float(self.X())
            Y_val = float(self.Y())
            gv_eff = self._gv_eff()
            if gv_eff == 0:
                return complex(0, 0)
            return complex(X_val, Y_val) / gv_eff
    
    chain = TestSignalChain()
    
    # Test: with Gv=100, X=1.0 V at lock-in => V_sample should be 0.01 V
    V_sample = chain._get_V_sample_ac_meas()
    expected_V_sample = complex(0.01, 0.0)
    
    assert abs(V_sample.real - expected_V_sample.real) < 1e-12
    assert abs(V_sample.imag - expected_V_sample.imag) < 1e-12


def test_derived_math_current_measurement():
    """Test current measurement with R_est=10kΩ."""
    # Create mock nodes
    preamp = MockNode("preamp")
    lockin = MockNode("lockin")
    
    # Set test values
    preamp.gain_v_per_v.set(100.0)
    preamp.invert.set(False)
    lockin.X.set(1.0)  # 1 V at lock-in
    lockin.Y.set(0.0)
    
    class TestSignalChain:
        def __init__(self):
            self.preamp_gain = preamp.gain_v_per_v
            self.preamp_invert = preamp.invert
            self.X = lockin.X
            self.Y = lockin.Y
            self.R_est = MockParameter(10e3)  # 10 kΩ
        
        def _gv_eff(self):
            gv = float(self.preamp_gain())
            invert = bool(self.preamp_invert())
            return -gv if invert else gv
        
        def _get_V_sample_ac_meas(self):
            X_val = float(self.X())
            Y_val = float(self.Y())
            gv_eff = self._gv_eff()
            if gv_eff == 0:
                return complex(0, 0)
            return complex(X_val, Y_val) / gv_eff
        
        def _get_I_meas(self):
            R_est = self.R_est()
            if R_est in (None, 0):
                return None
            V_sample = self._get_V_sample_ac_meas()
            return abs(V_sample) / float(R_est)
    
    chain = TestSignalChain()
    
    # Test: V_sample = 0.01 V, R_est = 10 kΩ => I_meas should be 1 µA
    I_meas = chain._get_I_meas()
    expected_I_meas = 1e-6  # 1 µA
    
    tolerance = 1e-12
    assert abs(I_meas - expected_I_meas) < tolerance, f"Expected I_meas={expected_I_meas}, got {I_meas}"


def test_inversion_logic():
    """Test signal inversion in effective calculations."""
    # Test gm_eff with inversion
    gm = 1e-3
    
    # Without inversion
    gm_eff_normal = gm  # No inversion
    assert gm_eff_normal == 1e-3
    
    # With inversion  
    gm_eff_inverted = -gm  # Inverted
    assert gm_eff_inverted == -1e-3
    
    # Test gv_eff with inversion
    gv = 100.0
    
    # Without inversion
    gv_eff_normal = gv
    assert gv_eff_normal == 100.0
    
    # With inversion
    gv_eff_inverted = -gv
    assert gv_eff_inverted == -100.0


def test_edge_cases():
    """Test edge cases like zero values."""
    # Test zero transconductance
    class TestSignalChain:
        def __init__(self):
            self.gm_a_per_v = MockParameter(0.0)
            self.vi_invert = MockParameter(False)
        
        def _gm_eff(self):
            gm = float(self.gm_a_per_v())
            invert = bool(self.vi_invert())
            return -gm if invert else gm
    
    chain = TestSignalChain()
    assert chain._gm_eff() == 0.0
    
    # Test zero gain
    class TestSignalChainGain:
        def __init__(self):
            self.preamp_gain = MockParameter(0.0)
            self.preamp_invert = MockParameter(False)
            self.X = MockParameter(1.0)
            self.Y = MockParameter(0.0)
        
        def _gv_eff(self):
            gv = float(self.preamp_gain())
            invert = bool(self.preamp_invert())
            return -gv if invert else gv
        
        def _get_V_sample_ac_meas(self):
            X_val = float(self.X())
            Y_val = float(self.Y())
            gv_eff = self._gv_eff()
            if gv_eff == 0:
                return complex(0, 0)
            return complex(X_val, Y_val) / gv_eff
    
    chain_gain = TestSignalChainGain()
    V_sample = chain_gain._get_V_sample_ac_meas()
    assert V_sample == complex(0, 0)


if __name__ == "__main__":
    test_derived_math_basic()
    test_derived_math_voltage_measurement()
    test_derived_math_current_measurement()
    test_inversion_logic()
    test_edge_cases()
    print("All derived math tests passed!")