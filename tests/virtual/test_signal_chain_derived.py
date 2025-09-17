"""Tests for signal chain derived math and physics calculations."""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock
from qcodes.parameters import ManualParameter
from qcodes_contrib_drivers.drivers.virtual.signal_chain_nodes import (
    MFLISource, ManualVITransformer, ManualVoltagePreamp, MFLILockIn
)
from qcodes_contrib_drivers.drivers.virtual.signal_chain import SignalChain


class TestSignalChainDerived:
    """Test derived math calculations in signal chain."""
    
    @pytest.fixture
    def mock_mfli(self):
        """Create mock MFLI instrument."""
        mock = Mock()
        mock.amplitude = ManualParameter('amplitude', initial_value=0.001, unit='V')
        mock.frequency = ManualParameter('frequency', initial_value=1000.0, unit='Hz')
        mock.output_on = ManualParameter('output_on', initial_value=True)
        mock.time_constant = ManualParameter('time_constant', initial_value=0.01, unit='s')
        mock.sensitivity = ManualParameter('sensitivity', initial_value=1e-3, unit='V')
        mock.input_range = ManualParameter('input_range', initial_value=1.0, unit='V')
        mock.X = ManualParameter('X', initial_value=1.0, unit='V')
        mock.Y = ManualParameter('Y', initial_value=0.0, unit='V')
        mock.R = ManualParameter('R', initial_value=1.0, unit='V')
        mock.Theta = ManualParameter('Theta', initial_value=0.0, unit='deg')
        return mock
    
    @pytest.fixture
    def signal_chain(self, mock_mfli):
        """Create signal chain with mock instruments."""
        src_v = MFLISource('src', mock_mfli)
        vi_transformer = ManualVITransformer('vi')
        preamp = ManualVoltagePreamp('preamp')
        lockin = MFLILockIn('lockin', mock_mfli)
        
        # Set up initial values
        vi_transformer.gm_a_per_v.set(1e-3)  # 1e-3 A/V
        vi_transformer.invert.set(False)
        preamp.gain_v_per_v.set(100.0)  # 100 V/V
        preamp.invert.set(False)
        
        return SignalChain(src_v, vi_transformer, preamp, lockin, name='test_chain')
    
    def test_current_setpoint_calculation(self, signal_chain):
        """Test I_set=1e-6 A results in excitation_v_ac=1e-3 V."""
        # Set target current
        I_target = 1e-6  # 1 µA
        
        signal_chain.I_set.set(I_target)
        
        # Check that excitation voltage is correctly calculated
        # V_needed = I_target / gm_eff = 1e-6 / 1e-3 = 1e-3 V
        expected_V = 1e-3
        actual_V = signal_chain.excitation_v_ac()
        
        assert abs(actual_V - expected_V) < 1e-12, f"Expected {expected_V}, got {actual_V}"
        assert signal_chain.output_on(), "Output should be turned on"
        
        # Check that I_cmd returns the same value
        assert abs(signal_chain.I_cmd() - I_target) < 1e-12
    
    def test_effective_transconductance(self, signal_chain):
        """Test effective transconductance with and without inversion."""
        # Test without inversion
        signal_chain.vi_invert.set(False)
        signal_chain.gm_a_per_v.set(1e-3)
        assert signal_chain._gm_eff() == 1e-3
        
        # Test with inversion
        signal_chain.vi_invert.set(True)
        assert signal_chain._gm_eff() == -1e-3
    
    def test_effective_preamp_gain(self, signal_chain):
        """Test effective preamp gain with and without inversion."""
        # Test without inversion
        signal_chain.preamp_invert.set(False)
        signal_chain.preamp_gain.set(100.0)
        assert signal_chain._gv_eff() == 100.0
        
        # Test with inversion
        signal_chain.preamp_invert.set(True)
        assert signal_chain._gv_eff() == -100.0
    
    def test_sample_voltage_measurement(self, signal_chain):
        """Test V_sample_ac_meas calculation from X,Y and preamp gain."""
        # Set up known values: X=1.0, Y=0.0, gain=100
        signal_chain.X.set(1.0)
        signal_chain.Y.set(0.0)
        signal_chain.preamp_gain.set(100.0)
        signal_chain.preamp_invert.set(False)
        
        V_sample = signal_chain.V_sample_ac_meas()
        
        # Expected: (1.0 + 0j) / 100 = 0.01 + 0j
        expected = complex(0.01, 0.0)
        assert abs(V_sample - expected) < 1e-12, f"Expected {expected}, got {V_sample}"
    
    def test_current_measurement(self, signal_chain):
        """Test I_meas calculation from V_sample and R_est."""
        # Set up conditions
        signal_chain.X.set(1.0)
        signal_chain.Y.set(0.0)
        signal_chain.preamp_gain.set(100.0)
        signal_chain.preamp_invert.set(False)
        signal_chain.R_est.set(10e3)  # 10 kΩ
        
        I_meas = signal_chain.I_meas()
        
        # V_sample = 0.01 V, R_est = 10e3 Ω
        # I_meas = |V_sample| / R_est = 0.01 / 10e3 = 1e-6 A
        expected = 1e-6
        assert abs(I_meas - expected) < 1e-12, f"Expected {expected}, got {I_meas}"
    
    def test_current_measurement_without_r_est(self, signal_chain):
        """Test I_meas returns None when R_est is not set."""
        signal_chain.R_est.set(None)
        assert signal_chain.I_meas() is None
        
        signal_chain.R_est.set(0)
        assert signal_chain.I_meas() is None
    
    def test_zero_transconductance_error(self, signal_chain):
        """Test that zero transconductance raises an error."""
        signal_chain.gm_a_per_v.set(0.0)
        
        with pytest.raises(ValueError, match="gm_a_per_v is zero"):
            signal_chain.I_set.set(1e-6)
    
    def test_recommended_sensitivity(self, signal_chain):
        """Test recommended sensitivity calculation."""
        signal_chain.R.set(0.5)  # 0.5 V reading
        signal_chain.margin.set(3.0)
        
        recommended = signal_chain.recommended_sensitivity()
        expected = 3.0 * 0.5  # margin * R
        
        assert abs(recommended - expected) < 1e-12, f"Expected {expected}, got {recommended}"