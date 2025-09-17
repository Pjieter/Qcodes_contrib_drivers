"""Tests for signal chain delegate parameters and frequency coupling."""

import pytest
from unittest.mock import Mock
from qcodes.parameters import ManualParameter
from qcodes_contrib_drivers.drivers.virtual.signal_chain_nodes import (
    MFLISource, ManualVITransformer, ManualVoltagePreamp, MFLILockIn
)
from qcodes_contrib_drivers.drivers.virtual.signal_chain import SignalChain


class TestSignalChainDelegates:
    """Test delegate parameters and frequency coupling."""
    
    @pytest.fixture
    def mock_mfli(self):
        """Create mock MFLI instrument with proper parameter behavior."""
        mock = Mock()
        
        # Create real ManualParameter instances for delegation
        mock.amplitude = ManualParameter('amplitude', initial_value=0.001, unit='V')
        mock.frequency = ManualParameter('frequency', initial_value=1000.0, unit='Hz')
        mock.output_on = ManualParameter('output_on', initial_value=False)
        mock.time_constant = ManualParameter('time_constant', initial_value=0.01, unit='s')
        mock.sensitivity = ManualParameter('sensitivity', initial_value=1e-3, unit='V')
        mock.input_range = ManualParameter('input_range', initial_value=1.0, unit='V')
        mock.X = ManualParameter('X', initial_value=0.0, unit='V')
        mock.Y = ManualParameter('Y', initial_value=0.0, unit='V')
        mock.R = ManualParameter('R', initial_value=0.0, unit='V')
        mock.Theta = ManualParameter('Theta', initial_value=0.0, unit='deg')
        
        return mock
    
    @pytest.fixture
    def signal_chain(self, mock_mfli):
        """Create signal chain with mock instruments."""
        src_v = MFLISource('src', mock_mfli)
        vi_transformer = ManualVITransformer('vi')
        preamp = ManualVoltagePreamp('preamp')
        lockin = MFLILockIn('lockin', mock_mfli)
        
        return SignalChain(src_v, vi_transformer, preamp, lockin, name='test_chain')
    
    def test_frequency_coupling(self, signal_chain, mock_mfli):
        """Test that reference_frequency writes both source and lock-in frequency."""
        test_freq = 1500.0  # Hz
        
        # Set the reference frequency
        signal_chain.reference_frequency.set(test_freq)
        
        # Check that both source and lock-in frequencies were set
        assert mock_mfli.frequency() == test_freq, "Source frequency not set correctly"
        assert signal_chain.lockin.frequency() == test_freq, "Lock-in frequency not set correctly"
        
        # Check that get returns the lock-in frequency
        assert signal_chain.reference_frequency() == test_freq
    
    def test_excitation_voltage_delegate(self, signal_chain, mock_mfli):
        """Test that excitation_v_ac delegates to source amplitude."""
        test_amplitude = 0.005  # V
        
        signal_chain.excitation_v_ac.set(test_amplitude)
        assert mock_mfli.amplitude() == test_amplitude
        
        # Test the reverse direction
        mock_mfli.amplitude.set(0.007)
        assert signal_chain.excitation_v_ac() == 0.007
    
    def test_output_on_delegate(self, signal_chain, mock_mfli):
        """Test that output_on delegates correctly."""
        signal_chain.output_on.set(True)
        assert mock_mfli.output_on() is True
        
        signal_chain.output_on.set(False)
        assert mock_mfli.output_on() is False
    
    def test_time_constant_delegate(self, signal_chain, mock_mfli):
        """Test time_constant delegation."""
        test_tc = 0.1  # s
        
        signal_chain.time_constant.set(test_tc)
        assert mock_mfli.time_constant() == test_tc
        
        mock_mfli.time_constant.set(0.05)
        assert signal_chain.time_constant() == 0.05
    
    def test_sensitivity_delegate(self, signal_chain, mock_mfli):
        """Test sensitivity delegation."""
        test_sens = 10e-6  # V
        
        signal_chain.sensitivity.set(test_sens)
        assert mock_mfli.sensitivity() == test_sens
    
    def test_input_range_delegate(self, signal_chain, mock_mfli):
        """Test input_range delegation."""
        test_range = 0.1  # V
        
        signal_chain.input_range.set(test_range)
        assert mock_mfli.input_range() == test_range
    
    def test_readout_delegates(self, signal_chain, mock_mfli):
        """Test X, Y, R, Theta readout delegation."""
        # Set values in mock
        mock_mfli.X.set(1.5)
        mock_mfli.Y.set(-0.5)
        mock_mfli.R.set(1.58)
        mock_mfli.Theta.set(18.4)
        
        # Check delegation works
        assert signal_chain.X() == 1.5
        assert signal_chain.Y() == -0.5
        assert signal_chain.R() == 1.58
        assert signal_chain.Theta() == 18.4
    
    def test_manual_parameter_delegates(self, signal_chain):
        """Test delegation of manual parameters."""
        # Test transconductance
        signal_chain.gm_a_per_v.set(2e-3)
        assert signal_chain.vi.gm_a_per_v() == 2e-3
        
        # Test V-I invert
        signal_chain.vi_invert.set(True)
        assert signal_chain.vi.invert() is True
        
        # Test preamp gain
        signal_chain.preamp_gain.set(50.0)
        assert signal_chain.preamp.gain_v_per_v() == 50.0
        
        # Test preamp invert
        signal_chain.preamp_invert.set(True)
        assert signal_chain.preamp.invert() is True
    
    def test_manual_advisory_parameters(self, signal_chain):
        """Test manual advisory parameters are accessible."""
        # Test R_est
        signal_chain.R_est.set(5000.0)
        assert signal_chain.R_est() == 5000.0
        
        # Test margin
        signal_chain.margin.set(2.5)
        assert signal_chain.margin() == 2.5
        
        # Test amplitude convention
        signal_chain.amplitude_convention.set("pp")
        assert signal_chain.amplitude_convention() == "pp"