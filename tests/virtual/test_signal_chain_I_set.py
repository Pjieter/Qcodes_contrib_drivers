"""Test current setpoint control and guard functions."""

import warnings
from unittest.mock import Mock, MagicMock

# Mock QCoDeS for testing
class MockParameter:
    def __init__(self, initial_value=0.0):
        self._value = initial_value
        self.set_calls = []
        self.get_calls = []
    
    def __call__(self):
        self.get_calls.append(None)
        return self._value
    
    def set(self, value):
        self.set_calls.append(value)
        self._value = value
    
    def get(self):
        self.get_calls.append(None)
        return self._value

class MockInstrument:
    def __init__(self, name):
        self.name = name
    
    def add_parameter(self, name, **kwargs):
        pass


def test_I_set_basic_functionality():
    """Test basic I_set functionality with open-loop control."""
    # Create mock nodes
    class MockSignalChain:
        def __init__(self):
            self.gm_a_per_v = MockParameter(1e-3)  # 1 mA/V
            self.vi_invert = MockParameter(False)
            self.excitation_v_ac = MockParameter(0.0)
            self.output_on = MockParameter(False)
            self.R_est = MockParameter(10e3)  # 10 kΩ
            self.preamp_gain = MockParameter(100.0)
            self.preamp_invert = MockParameter(False)
            self.input_range = MockParameter(1.0)  # 1V input range
        
        def _gm_eff(self):
            gm = float(self.gm_a_per_v())
            invert = bool(self.vi_invert())
            return -gm if invert else gm
        
        def _gv_eff(self):
            gv = float(self.preamp_gain())
            invert = bool(self.preamp_invert())
            return -gv if invert else gv
        
        def _guard_lockin_overload(self, I_target):
            """Check for potential lock-in input overload and warn."""
            R_est = self.R_est()
            if R_est in (None, 0):
                return
            
            V_preamp_out_pred = abs(I_target) * float(R_est) * abs(self._gv_eff())
            input_range = float(self.input_range())
            threshold = 0.8 * input_range
            
            if V_preamp_out_pred > threshold:
                warnings.warn(
                    f"[GUARD] Predicted lock-in input {V_preamp_out_pred:.3g} V "
                    f"exceeds 80% of input range {input_range:.3g} V.",
                    UserWarning
                )
        
        def set_I_target(self, I_target):
            """Set target current by computing required source voltage."""
            gm_eff = self._gm_eff()
            if gm_eff == 0:
                raise ValueError("gm_a_per_v is zero; cannot compute source voltage.")
            
            V_needed = I_target / gm_eff
            self._guard_lockin_overload(I_target)
            self.excitation_v_ac.set(V_needed)
            self.output_on.set(True)
        
        def get_I_cmd(self):
            """Get commanded current based on current source voltage."""
            return self._gm_eff() * float(self.excitation_v_ac())
    
    chain = MockSignalChain()
    
    # Test I_set = 1e-6 A with gm = 1e-3 A/V
    I_target = 1e-6  # 1 µA
    chain.set_I_target(I_target)
    
    # Verify source voltage was set correctly
    expected_V = I_target / 1e-3  # 1e-6 / 1e-3 = 1e-3 V
    assert abs(chain.excitation_v_ac() - expected_V) < 1e-12
    assert expected_V in chain.excitation_v_ac.set_calls
    
    # Verify output was turned on
    assert chain.output_on() == True
    assert True in chain.output_on.set_calls
    
    # Verify I_cmd returns the correct value
    I_cmd = chain.get_I_cmd()
    assert abs(I_cmd - I_target) < 1e-12


def test_I_set_with_inversion():
    """Test I_set with signal inversion."""
    class MockSignalChain:
        def __init__(self):
            self.gm_a_per_v = MockParameter(1e-3)
            self.vi_invert = MockParameter(True)  # Inverted
            self.excitation_v_ac = MockParameter(0.0)
            self.output_on = MockParameter(False)
            self.R_est = MockParameter(None)  # No R_est to skip guard
        
        def _gm_eff(self):
            gm = float(self.gm_a_per_v())
            invert = bool(self.vi_invert())
            return -gm if invert else gm
        
        def _guard_lockin_overload(self, I_target):
            pass  # Skip guard for this test
        
        def set_I_target(self, I_target):
            gm_eff = self._gm_eff()
            if gm_eff == 0:
                raise ValueError("gm_a_per_v is zero; cannot compute source voltage.")
            
            V_needed = I_target / gm_eff
            self._guard_lockin_overload(I_target)
            self.excitation_v_ac.set(V_needed)
            self.output_on.set(True)
        
        def get_I_cmd(self):
            return self._gm_eff() * float(self.excitation_v_ac())
    
    chain = MockSignalChain()
    
    # Test with inversion: gm_eff = -1e-3
    I_target = 1e-6
    gm_eff = chain._gm_eff()
    assert gm_eff == -1e-3  # Should be negative due to inversion
    
    chain.set_I_target(I_target)
    
    # With inverted gm, V_needed should be negative
    expected_V = I_target / (-1e-3)  # 1e-6 / (-1e-3) = -1e-3 V
    assert abs(chain.excitation_v_ac() - expected_V) < 1e-12
    
    # I_cmd should still match I_target
    I_cmd = chain.get_I_cmd()
    assert abs(I_cmd - I_target) < 1e-12


def test_I_set_zero_transconductance_error():
    """Test I_set raises error when transconductance is zero."""
    class MockSignalChain:
        def __init__(self):
            self.gm_a_per_v = MockParameter(0.0)  # Zero transconductance
            self.vi_invert = MockParameter(False)
        
        def _gm_eff(self):
            gm = float(self.gm_a_per_v())
            invert = bool(self.vi_invert())
            return -gm if invert else gm
        
        def set_I_target(self, I_target):
            gm_eff = self._gm_eff()
            if gm_eff == 0:
                raise ValueError("gm_a_per_v is zero; cannot compute source voltage.")
    
    chain = MockSignalChain()
    
    # Should raise ValueError for zero transconductance
    try:
        chain.set_I_target(1e-6)
        assert False, "Expected ValueError but none was raised"
    except ValueError as e:
        assert "gm_a_per_v is zero" in str(e)


def test_guard_function_warning():
    """Test guard function warns when predicted input exceeds threshold."""
    class MockSignalChain:
        def __init__(self):
            self.R_est = MockParameter(10e3)  # 10 kΩ
            self.preamp_gain = MockParameter(100.0)  # 100 V/V
            self.preamp_invert = MockParameter(False)
            self.input_range = MockParameter(1.0)  # 1V input range
        
        def _gv_eff(self):
            gv = float(self.preamp_gain())
            invert = bool(self.preamp_invert())
            return -gv if invert else gv
        
        def _guard_lockin_overload(self, I_target):
            R_est = self.R_est()
            if R_est in (None, 0):
                return
            
            V_preamp_out_pred = abs(I_target) * float(R_est) * abs(self._gv_eff())
            input_range = float(self.input_range())
            threshold = 0.8 * input_range
            
            if V_preamp_out_pred > threshold:
                warnings.warn(
                    f"[GUARD] Predicted lock-in input {V_preamp_out_pred:.3g} V "
                    f"exceeds 80% of input range {input_range:.3g} V.",
                    UserWarning
                )
    
    chain = MockSignalChain()
    
    # Test case: R_est=10kΩ, gain=100, I_target=1µA
    # Predicted V_preamp_out = 1e-6 * 10e3 * 100 = 1.0 V
    # Input range = 1.0 V, threshold = 0.8 V
    # Should warn since 1.0 V > 0.8 V
    
    I_target = 1e-6
    
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        chain._guard_lockin_overload(I_target)
        
        # Should have issued a warning
        assert len(w) == 1
        assert "GUARD" in str(w[0].message)
        assert "exceeds 80%" in str(w[0].message)
        assert "1 V" in str(w[0].message)


def test_guard_function_no_warning_under_threshold():
    """Test guard function doesn't warn when under threshold."""
    class MockSignalChain:
        def __init__(self):
            self.R_est = MockParameter(1e3)  # 1 kΩ (smaller resistance)
            self.preamp_gain = MockParameter(100.0)
            self.preamp_invert = MockParameter(False)
            self.input_range = MockParameter(1.0)
        
        def _gv_eff(self):
            gv = float(self.preamp_gain())
            invert = bool(self.preamp_invert())
            return -gv if invert else gv
        
        def _guard_lockin_overload(self, I_target):
            R_est = self.R_est()
            if R_est in (None, 0):
                return
            
            V_preamp_out_pred = abs(I_target) * float(R_est) * abs(self._gv_eff())
            input_range = float(self.input_range())
            threshold = 0.8 * input_range
            
            if V_preamp_out_pred > threshold:
                warnings.warn(
                    f"[GUARD] Predicted lock-in input {V_preamp_out_pred:.3g} V "
                    f"exceeds 80% of input range {input_range:.3g} V.",
                    UserWarning
                )
    
    chain = MockSignalChain()
    
    # Test case: R_est=1kΩ, gain=100, I_target=1µA
    # Predicted V_preamp_out = 1e-6 * 1e3 * 100 = 0.1 V
    # Threshold = 0.8 V
    # Should NOT warn since 0.1 V < 0.8 V
    
    I_target = 1e-6
    
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        chain._guard_lockin_overload(I_target)
        
        # Should not have issued a warning
        assert len(w) == 0


def test_guard_function_skips_without_r_est():
    """Test guard function skips when R_est is None or zero."""
    class MockSignalChain:
        def __init__(self):
            self.R_est = MockParameter(None)  # No resistance estimate
            self.preamp_gain = MockParameter(100.0)
            self.preamp_invert = MockParameter(False)
            self.input_range = MockParameter(1.0)
        
        def _gv_eff(self):
            gv = float(self.preamp_gain())
            invert = bool(self.preamp_invert())
            return -gv if invert else gv
        
        def _guard_lockin_overload(self, I_target):
            R_est = self.R_est()
            if R_est in (None, 0):
                return  # Skip guard
            
            # This should not be reached
            assert False, "Guard should have been skipped"
    
    chain = MockSignalChain()
    
    # Should not raise any warnings or errors
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        chain._guard_lockin_overload(1e-6)
        assert len(w) == 0
    
    # Test with R_est = 0
    chain.R_est.set(0.0)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        chain._guard_lockin_overload(1e-6)
        assert len(w) == 0


def test_I_set_negative_current():
    """Test I_set with negative current values."""
    class MockSignalChain:
        def __init__(self):
            self.gm_a_per_v = MockParameter(1e-3)
            self.vi_invert = MockParameter(False)
            self.excitation_v_ac = MockParameter(0.0)
            self.output_on = MockParameter(False)
            self.R_est = MockParameter(None)  # Skip guard
        
        def _gm_eff(self):
            gm = float(self.gm_a_per_v())
            invert = bool(self.vi_invert())
            return -gm if invert else gm
        
        def _guard_lockin_overload(self, I_target):
            pass
        
        def set_I_target(self, I_target):
            gm_eff = self._gm_eff()
            if gm_eff == 0:
                raise ValueError("gm_a_per_v is zero; cannot compute source voltage.")
            
            V_needed = I_target / gm_eff
            self._guard_lockin_overload(I_target)
            self.excitation_v_ac.set(V_needed)
            self.output_on.set(True)
        
        def get_I_cmd(self):
            return self._gm_eff() * float(self.excitation_v_ac())
    
    chain = MockSignalChain()
    
    # Test negative current
    I_target = -1e-6  # -1 µA
    chain.set_I_target(I_target)
    
    expected_V = I_target / 1e-3  # -1e-6 / 1e-3 = -1e-3 V
    assert abs(chain.excitation_v_ac() - expected_V) < 1e-12
    
    I_cmd = chain.get_I_cmd()
    assert abs(I_cmd - I_target) < 1e-12


if __name__ == "__main__":
    test_I_set_basic_functionality()
    test_I_set_with_inversion()
    test_I_set_zero_transconductance_error()
    test_guard_function_warning()
    test_guard_function_no_warning_under_threshold()
    test_guard_function_skips_without_r_est()
    test_I_set_negative_current()
    print("All I_set tests passed!")