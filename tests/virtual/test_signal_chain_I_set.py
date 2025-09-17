"""Tests for signal chain I_set parameter and guard functions."""

import pytest
from unittest.mock import Mock, patch
from io import StringIO
import sys
from qcodes.parameters import ManualParameter
from qcodes_contrib_drivers.drivers.virtual.signal_chain_nodes import (
    MFLISource, ManualVITransformer, ManualVoltagePreamp, MFLILockIn
)
from qcodes_contrib_drivers.drivers.virtual.signal_chain import SignalChain


class TestSignalChainISet:
    """Test I_set parameter and guard functions."""
    
    @pytest.fixture
    def mock_mfli(self):
        """Create mock MFLI instrument."""
        mock = Mock()
        mock.amplitude = ManualParameter('amplitude', initial_value=0.0, unit='V')
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
        """Create signal chain with known parameters for guard testing."""
        src_v = MFLISource('src', mock_mfli)
        vi_transformer = ManualVITransformer('vi')
        preamp = ManualVoltagePreamp('preamp')
        lockin = MFLILockIn('lockin', mock_mfli)
        
        # Set up for guard test conditions
        vi_transformer.gm_a_per_v.set(1e-3)  # 1e-3 A/V
        vi_transformer.invert.set(False)
        preamp.gain_v_per_v.set(100.0)  # 100 V/V
        preamp.invert.set(False)
        
        chain = SignalChain(src_v, vi_transformer, preamp, lockin, name='test_chain')
        chain.R_est.set(10e3)  # 10 kΩ
        chain.input_range.set(1.0)  # 1 V range
        
        return chain
    
    def test_i_set_basic_operation(self, signal_chain):
        """Test basic I_set operation."""
        I_target = 1e-6  # 1 µA
        
        signal_chain.I_set.set(I_target)
        
        # Check amplitude was set correctly
        expected_V = I_target / 1e-3  # I_target / gm
        assert abs(signal_chain.excitation_v_ac() - expected_V) < 1e-12
        
        # Check output was turned on
        assert signal_chain.output_on() is True
        
        # Check I_cmd returns the target
        assert abs(signal_chain.I_cmd() - I_target) < 1e-12
    
    def test_i_set_with_inversion(self, signal_chain):
        """Test I_set with V-I transformer inversion."""
        signal_chain.vi_invert.set(True)  # Inverted transconductance
        I_target = 1e-6  # 1 µA
        
        signal_chain.I_set.set(I_target)
        
        # With inversion, gm_eff = -1e-3, so V_needed = 1e-6 / (-1e-3) = -1e-3
        # But amplitude should be positive (magnitude)
        expected_V = abs(I_target / -1e-3)  # 1e-3 V
        assert abs(signal_chain.excitation_v_ac() - expected_V) < 1e-12
    
    def test_guard_function_warning(self, signal_chain):
        """Test that guard function warns when predicted input exceeds range."""
        # Set up conditions that will trigger guard
        # R_est=10kΩ, gain=100, input_range=1V
        # For I_target=1e-6: V_preamp_out = 1e-6 * 10e3 * 100 = 1V
        # This equals the input range, should trigger warning at 80% threshold
        
        I_target = 1e-6  # This should give exactly 1V at preamp output
        
        # Capture print output
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            signal_chain.I_set.set(I_target)
        
        output = captured_output.getvalue()
        assert "[guard]" in output, "Guard warning should be printed"
        assert "exceeds 80%" in output, "Should mention 80% threshold"
    
    def test_guard_function_no_warning_safe_level(self, signal_chain):
        """Test that guard function doesn't warn for safe levels."""
        # Set a current that results in well below 80% of range
        I_target = 1e-7  # Much smaller current
        
        # Capture print output
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            signal_chain.I_set.set(I_target)
        
        output = captured_output.getvalue()
        assert "[guard]" not in output, "No guard warning should be printed for safe levels"
    
    def test_guard_function_without_r_est(self, signal_chain):
        """Test that guard function is skipped when R_est is None."""
        signal_chain.R_est.set(None)  # No resistance estimate
        
        # This should not raise an error or print warnings
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            signal_chain.I_set.set(1e-6)
        
        output = captured_output.getvalue()
        assert "[guard]" not in output, "No guard warning when R_est is None"
    
    def test_guard_calculation_accuracy(self, signal_chain):
        """Test the accuracy of guard calculation."""
        # Set up precise conditions
        signal_chain.R_est.set(10e3)  # 10 kΩ
        signal_chain.preamp_gain.set(100.0)  # 100 V/V
        signal_chain.preamp_invert.set(False)
        signal_chain.input_range.set(1.0)  # 1 V
        
        I_target = 1e-6  # 1 µA
        
        # Calculate expected preamp output
        # V_preamp_out = |I_target| * R_est * |Gv_eff| = 1e-6 * 10e3 * 100 = 1.0 V
        expected_preamp_out = abs(I_target) * 10e3 * 100
        assert expected_preamp_out == 1.0, "Test setup should give 1V preamp output"
        
        # This should trigger warning since 1.0 V > 0.8 * 1.0 V
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            signal_chain.I_set.set(I_target)
        
        output = captured_output.getvalue()
        assert "1 V exceeds 80% of 1 V" in output, "Guard should show exact calculation"
    
    def test_zero_gm_error(self, signal_chain):
        """Test error when transconductance is zero."""
        signal_chain.gm_a_per_v.set(0.0)
        
        with pytest.raises(ValueError, match="gm_a_per_v is zero"):
            signal_chain.I_set.set(1e-6)
    
    def test_i_set_roundtrip(self, signal_chain):
        """Test that I_set and I_cmd are consistent."""
        test_currents = [1e-9, 1e-6, 10e-6, 100e-6]
        
        for I_target in test_currents:
            signal_chain.I_set.set(I_target)
            I_readback = signal_chain.I_cmd()
            assert abs(I_readback - I_target) < 1e-15, f"Roundtrip failed for {I_target}"