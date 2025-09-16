"""
Tests for manual IVVI rack modules.

These tests verify the basic functionality of the manual IVVI modules
including parameter creation, validation, and basic operations.
"""

import pytest
from qcodes_contrib_drivers.drivers.QuTech.IVVI_Modules import (
    IVVI_Module,
    S4c,
    M2m,
    M2b,
    M1b,
    VId,
    IVd,
)


class TestIVVIModule:
    """Test the base IVVI_Module class."""

    def test_initialization(self):
        """Test that the base module can be initialized."""
        module = IVVI_Module("test_module")
        assert module.name == "test_module"
        assert hasattr(module, "module_type")
        assert hasattr(module, "rack_position")
        assert hasattr(module, "notes")

    def test_idn(self):
        """Test the get_idn method."""
        module = IVVI_Module("test_module")
        idn = module.get_idn()
        assert idn["vendor"] == "QuTech"
        assert "IVVI" in idn["model"]
        assert idn["serial"] == "Manual"
        assert idn["firmware"] == "N/A"

    def test_common_parameters(self):
        """Test that common parameters are properly set."""
        module = IVVI_Module("test_module")
        module.module_type("TestType")
        module.rack_position("Slot 1")
        module.notes("Test notes")

        assert module.module_type() == "TestType"
        assert module.rack_position() == "Slot 1"
        assert module.notes() == "Test notes"


class TestS4c:
    """Test the S4c current source module."""

    def test_initialization(self):
        """Test S4c initialization."""
        s4c = S4c("s4c_test")
        assert s4c.name == "s4c_test"
        assert s4c.module_type() == "S4c"

    def test_channel_parameters(self):
        """Test that all 4 channels are created with proper parameters."""
        s4c = S4c("s4c_test")

        for i in range(1, 5):
            assert hasattr(s4c, f"ch{i}_current")
            assert hasattr(s4c, f"ch{i}_enabled")

            # Test parameter initial values
            assert s4c.parameters[f"ch{i}_current"]() == 0.0
            assert s4c.parameters[f"ch{i}_enabled"]() is False

    def test_current_range(self):
        """Test current range parameter."""
        s4c = S4c("s4c_test")
        assert s4c.current_range() == "10uA"

    def test_resolution(self):
        """Test resolution calculation."""
        s4c = S4c("s4c_test")
        resolution = s4c.resolution()
        expected = (2 * 10e-6) / (2**16)  # 20μA / 65536
        assert abs(resolution - expected) < 1e-12

    def test_current_validation(self):
        """Test current parameter validation."""
        s4c = S4c("s4c_test")

        # Test valid values
        s4c.ch1_current(5e-6)  # 5 μA
        assert s4c.ch1_current() == 5e-6

        # Test boundary values
        s4c.ch1_current(10e-6)  # +10 μA
        s4c.ch1_current(-10e-6)  # -10 μA

        # Test invalid values (should raise)
        with pytest.raises(ValueError):
            s4c.ch1_current(11e-6)  # Too high
        with pytest.raises(ValueError):
            s4c.ch1_current(-11e-6)  # Too low


class TestM2m:
    """Test the M2m voltage source module."""

    def test_initialization(self):
        """Test M2m initialization."""
        m2m = M2m("m2m_test")
        assert m2m.name == "m2m_test"
        assert m2m.module_type() == "M2m"

    def test_channel_parameters(self):
        """Test that 2 channels are created with proper parameters."""
        m2m = M2m("m2m_test")

        for i in range(1, 3):
            assert hasattr(m2m, f"ch{i}_voltage")
            assert hasattr(m2m, f"ch{i}_enabled")

            # Test parameter initial values
            assert m2m.parameters[f"ch{i}_voltage"]() == 0.0
            assert m2m.parameters[f"ch{i}_enabled"]() is False

    def test_voltage_range(self):
        """Test voltage range parameter."""
        m2m = M2m("m2m_test")
        assert m2m.voltage_range() == "±4V"

    def test_voltage_validation(self):
        """Test voltage parameter validation."""
        m2m = M2m("m2m_test")

        # Test valid values
        m2m.ch1_voltage(2.0)  # 2V
        assert m2m.ch1_voltage() == 2.0

        # Test boundary values
        m2m.ch1_voltage(4.0)  # +4V
        m2m.ch1_voltage(-4.0)  # -4V

        # Test invalid values
        with pytest.raises(ValueError):
            m2m.ch1_voltage(4.1)  # Too high
        with pytest.raises(ValueError):
            m2m.ch1_voltage(-4.1)  # Too low


class TestM2b:
    """Test the M2b voltage source module."""

    def test_initialization(self):
        """Test M2b initialization."""
        m2b = M2b("m2b_test")
        assert m2b.name == "m2b_test"
        assert m2b.module_type() == "M2b"

    def test_similar_to_m2m(self):
        """Test that M2b has similar functionality to M2m."""
        m2b = M2b("m2b_test")

        # Should have same voltage range and resolution as M2m
        assert m2b.voltage_range() == "±4V"

        # Should have 2 channels
        for i in range(1, 3):
            assert hasattr(m2b, f"ch{i}_voltage")
            assert hasattr(m2b, f"ch{i}_enabled")


class TestM1b:
    """Test the M1b voltage source module."""

    def test_initialization(self):
        """Test M1b initialization."""
        m1b = M1b("m1b_test")
        assert m1b.name == "m1b_test"
        assert m1b.module_type() == "M1b"

    def test_single_channel(self):
        """Test that M1b has only one channel."""
        m1b = M1b("m1b_test")

        # Should have only channel 1
        assert hasattr(m1b, "ch1_voltage")
        assert hasattr(m1b, "ch1_enabled")

        # Should not have channel 2
        assert not hasattr(m1b, "ch2_voltage")
        assert not hasattr(m1b, "ch2_enabled")


class TestVId:
    """Test the VId voltage measurement module."""

    def test_initialization_default(self):
        """Test VId initialization with default channels."""
        vid = VId("vid_test")
        assert vid.name == "vid_test"
        assert vid.module_type() == "VId"
        assert vid.num_channels() == 8  # Default

    def test_initialization_custom_channels(self):
        """Test VId initialization with custom channel count."""
        vid = VId("vid_test", num_channels=4)
        assert vid.num_channels() == 4

    def test_channel_parameters(self):
        """Test measurement channel parameters."""
        vid = VId("vid_test", num_channels=4)

        for i in range(1, 5):
            assert hasattr(vid, f"ch{i}_voltage")
            assert hasattr(vid, f"ch{i}_enabled")

            # Test initial values (measurements default to enabled)
            assert vid.parameters[f"ch{i}_voltage"]() == 0.0
            assert vid.parameters[f"ch{i}_enabled"]() is True

    def test_measurement_range(self):
        """Test measurement range parameter."""
        vid = VId("vid_test")
        assert vid.measurement_range() == "±10V"


class TestIVd:
    """Test the IVd source-measure module."""

    def test_initialization_default(self):
        """Test IVd initialization with default channels."""
        ivd = IVd("ivd_test")
        assert ivd.name == "ivd_test"
        assert ivd.module_type() == "IVd"
        assert ivd.num_channels() == 4  # Default

    def test_initialization_custom_channels(self):
        """Test IVd initialization with custom channel count."""
        ivd = IVd("ivd_test", num_channels=2)
        assert ivd.num_channels() == 2

    def test_source_measure_parameters(self):
        """Test that each channel has both source and measure parameters."""
        ivd = IVd("ivd_test", num_channels=2)

        for i in range(1, 3):
            # Source parameters
            assert hasattr(ivd, f"ch{i}_voltage")
            assert hasattr(ivd, f"ch{i}_source_enabled")

            # Measure parameters
            assert hasattr(ivd, f"ch{i}_current")
            assert hasattr(ivd, f"ch{i}_measure_enabled")

            # Test initial values
            assert ivd.parameters[f"ch{i}_voltage"]() == 0.0
            assert ivd.parameters[f"ch{i}_source_enabled"]() is False
            assert ivd.parameters[f"ch{i}_current"]() == 0.0
            assert ivd.parameters[f"ch{i}_measure_enabled"]() is True

    def test_ranges(self):
        """Test voltage and current ranges."""
        ivd = IVd("ivd_test")
        assert ivd.voltage_range() == "±4V"
        assert ivd.current_range() == "±100uA"

    def test_resolutions(self):
        """Test voltage and current resolutions."""
        ivd = IVd("ivd_test")

        v_res = ivd.voltage_resolution()
        expected_v = (2 * 4.0) / (2**16)  # 8V / 65536
        assert abs(v_res - expected_v) < 1e-12

        i_res = ivd.current_resolution()
        expected_i = (2 * 100e-6) / (2**16)  # 200μA / 65536
        assert abs(i_res - expected_i) < 1e-12


class TestModuleInstantiation:
    """Test that modules can be instantiated and work together."""

    def test_multiple_modules(self):
        """Test creating multiple modules simultaneously."""
        modules = {
            "s4c": S4c("current_source"),
            "m2m": M2m("voltage_source_1"),
            "m2b": M2b("voltage_source_2"),
            "m1b": M1b("single_voltage"),
            "vid": VId("voltmeter"),
            "ivd": IVd("source_measure"),
        }

        # All should be properly initialized
        for name, module in modules.items():
            assert module.name == module.name
            assert "IVVI" in module.get_idn()["model"]

    def test_module_configuration(self):
        """Test configuring modules for a typical measurement setup."""
        # Create a typical setup
        current_source = S4c("cs1")
        voltage_source = M2m("vs1")
        voltmeter = VId("vm1", num_channels=4)
        smu = IVd("smu1", num_channels=2)

        # Configure the setup
        current_source.rack_position("Slot 1")
        voltage_source.rack_position("Slot 2")
        voltmeter.rack_position("Slot 3")
        smu.rack_position("Slot 4")

        # Set some typical values
        current_source.ch1_enabled(True)
        current_source.ch1_current(1e-6)  # 1 μA

        voltage_source.ch1_enabled(True)
        voltage_source.ch1_voltage(0.5)  # 0.5 V

        # Verify the configuration
        assert current_source.rack_position() == "Slot 1"
        assert current_source.ch1_current() == 1e-6
        assert voltage_source.ch1_voltage() == 0.5
