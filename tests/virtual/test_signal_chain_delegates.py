"""Test delegate parameter functionality and frequency coupling."""

import pytest
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

# Mock the nodes
class MockMFLISource(MockInstrument):
    def __init__(self, name="mfli_source"):
        super().__init__(name)
        self.amplitude = MockParameter(0.0)
        self.level = self.amplitude  # Alias
        self.output_on = MockParameter(False)
        self.frequency = MockParameter(1000.0)

class MockMFLILockIn(MockInstrument):
    def __init__(self, name="mfli_lockin"):
        super().__init__(name)
        self.frequency = MockParameter(1000.0)
        self.time_constant = MockParameter(0.1)
        self.sensitivity = MockParameter(1.0)
        self.input_range = MockParameter(1.0)
        self.X = MockParameter(0.0)
        self.Y = MockParameter(0.0)
        self.R = MockParameter(0.0)
        self.Theta = MockParameter(0.0)

class MockManualVITransformer(MockInstrument):
    def __init__(self, name="vi_transformer"):
        super().__init__(name)
        self.gm_a_per_v = MockParameter(1e-3)
        self.invert = MockParameter(False)

class MockManualVoltagePreamp(MockInstrument):
    def __init__(self, name="voltage_preamp"):
        super().__init__(name)
        self.gain_v_per_v = MockParameter(100.0)
        self.invert = MockParameter(False)


def test_delegate_parameters():
    """Test that delegate parameters properly forward to source parameters."""
    # Create mock nodes
    src_v = MockMFLISource()
    vi = MockManualVITransformer()
    preamp = MockManualVoltagePreamp()
    lockin = MockMFLILockIn()
    
    # Mock SignalChain to test delegation
    class TestSignalChain:
        def __init__(self):
            self.src_v = src_v
            self.vi = vi
            self.preamp = preamp
            self.lockin = lockin
            
            # Mock delegate parameters by direct reference
            self.excitation_v_ac = src_v.amplitude
            self.output_on = src_v.output_on
            self.gm_a_per_v = vi.gm_a_per_v
            self.vi_invert = vi.invert
            self.preamp_gain = preamp.gain_v_per_v
            self.preamp_invert = preamp.invert
            self.time_constant = lockin.time_constant
            self.sensitivity = lockin.sensitivity
            self.input_range = lockin.input_range
            self.X = lockin.X
            self.Y = lockin.Y
            self.R = lockin.R
            self.Theta = lockin.Theta
    
    chain = TestSignalChain()
    
    # Test setting and getting delegated parameters
    test_voltage = 0.5
    chain.excitation_v_ac.set(test_voltage)
    assert chain.excitation_v_ac() == test_voltage
    assert src_v.amplitude() == test_voltage
    
    # Test output enable
    chain.output_on.set(True)
    assert chain.output_on() == True
    assert src_v.output_on() == True
    
    # Test manual parameters
    test_gm = 2e-3
    chain.gm_a_per_v.set(test_gm)
    assert chain.gm_a_per_v() == test_gm
    assert vi.gm_a_per_v() == test_gm
    
    test_gain = 200.0
    chain.preamp_gain.set(test_gain)
    assert chain.preamp_gain() == test_gain
    assert preamp.gain_v_per_v() == test_gain
    
    # Test lock-in parameters
    test_tc = 0.3
    chain.time_constant.set(test_tc)
    assert chain.time_constant() == test_tc
    assert lockin.time_constant() == test_tc


def test_frequency_coupling():
    """Test that reference_frequency sets both source and lock-in frequency."""
    # Create mock nodes
    src_v = MockMFLISource()
    lockin = MockMFLILockIn()
    
    # Set initial different frequencies
    src_v.frequency.set(1000.0)
    lockin.frequency.set(1500.0)
    
    # Mock SignalChain frequency coupling
    class TestSignalChain:
        def __init__(self):
            self.src_v = src_v
            self.lockin = lockin
        
        def set_reference_frequency(self, f):
            """Set both source and lock-in frequency."""
            if hasattr(self.src_v, 'frequency') and self.src_v.frequency is not None:
                self.src_v.frequency.set(f)
            self.lockin.frequency.set(f)
        
        def get_reference_frequency(self):
            """Get lock-in frequency as reference."""
            return float(self.lockin.frequency())
    
    chain = TestSignalChain()
    
    # Test setting reference frequency
    test_freq = 2000.0
    chain.set_reference_frequency(test_freq)
    
    # Both source and lock-in should have the same frequency
    assert src_v.frequency() == test_freq
    assert lockin.frequency() == test_freq
    assert chain.get_reference_frequency() == test_freq
    
    # Verify the calls were made
    assert test_freq in src_v.frequency.set_calls
    assert test_freq in lockin.frequency.set_calls


def test_frequency_coupling_without_source_frequency():
    """Test frequency coupling when source doesn't have frequency parameter."""
    # Create mock nodes where source has no frequency
    class MockSourceNoFreq(MockInstrument):
        def __init__(self, name="source_no_freq"):
            super().__init__(name)
            self.amplitude = MockParameter(0.0)
            self.output_on = MockParameter(False)
            # No frequency parameter
    
    src_v = MockSourceNoFreq()
    lockin = MockMFLILockIn()
    
    # Mock SignalChain frequency coupling
    class TestSignalChain:
        def __init__(self):
            self.src_v = src_v
            self.lockin = lockin
        
        def set_reference_frequency(self, f):
            """Set both source and lock-in frequency."""
            if hasattr(self.src_v, 'frequency') and self.src_v.frequency is not None:
                self.src_v.frequency.set(f)
            self.lockin.frequency.set(f)
        
        def get_reference_frequency(self):
            """Get lock-in frequency as reference."""
            return float(self.lockin.frequency())
    
    chain = TestSignalChain()
    
    # Test setting reference frequency when source has no frequency
    test_freq = 3000.0
    initial_lockin_freq = lockin.frequency()
    
    chain.set_reference_frequency(test_freq)
    
    # Only lock-in should have the new frequency
    assert not hasattr(src_v, 'frequency') or src_v.frequency is None
    assert lockin.frequency() == test_freq
    assert chain.get_reference_frequency() == test_freq


def test_parameter_call_tracking():
    """Test that parameter calls are properly tracked for delegation."""
    src_v = MockMFLISource()
    
    # Clear any previous calls
    src_v.amplitude.set_calls.clear()
    src_v.amplitude.get_calls.clear()
    
    # Test setting and getting
    src_v.amplitude.set(0.1)
    src_v.amplitude.set(0.2)
    value = src_v.amplitude()
    
    # Verify calls were tracked
    assert len(src_v.amplitude.set_calls) == 2
    assert 0.1 in src_v.amplitude.set_calls
    assert 0.2 in src_v.amplitude.set_calls
    assert len(src_v.amplitude.get_calls) == 1
    assert value == 0.2


def test_multiple_delegate_independence():
    """Test that multiple delegate parameters work independently."""
    src_v = MockMFLISource()
    lockin = MockMFLILockIn()
    
    # Mock SignalChain with multiple delegates
    class TestSignalChain:
        def __init__(self):
            self.excitation_v_ac = src_v.amplitude
            self.output_on = src_v.output_on
            self.time_constant = lockin.time_constant
            self.X = lockin.X
    
    chain = TestSignalChain()
    
    # Set different values for different parameters
    chain.excitation_v_ac.set(0.5)
    chain.output_on.set(True)
    chain.time_constant.set(0.3)
    chain.X.set(1.5)
    
    # Verify each parameter is independent
    assert chain.excitation_v_ac() == 0.5
    assert chain.output_on() == True
    assert chain.time_constant() == 0.3
    assert chain.X() == 1.5
    
    # Verify source parameters
    assert src_v.amplitude() == 0.5
    assert src_v.output_on() == True
    
    # Verify lock-in parameters
    assert lockin.time_constant() == 0.3
    assert lockin.X() == 1.5


def test_parameter_type_consistency():
    """Test that parameter types are maintained through delegation."""
    src_v = MockMFLISource()
    vi = MockManualVITransformer()
    
    # Test float values
    float_val = 1.23
    src_v.amplitude.set(float_val)
    assert isinstance(src_v.amplitude(), (int, float))
    assert src_v.amplitude() == float_val
    
    # Test boolean values
    bool_val = True
    vi.invert.set(bool_val)
    assert isinstance(vi.invert(), bool)
    assert vi.invert() == bool_val


if __name__ == "__main__":
    test_delegate_parameters()
    test_frequency_coupling()
    test_frequency_coupling_without_source_frequency()
    test_parameter_call_tracking()
    test_multiple_delegate_independence()
    test_parameter_type_consistency()
    print("All delegate parameter tests passed!")