"""
Tests for QuTech IVVI manual modules.

These tests verify the basic functionality of the manual IVVI modules
following the pattern from test_keithley_26xx.py.
"""

import pytest

from qcodes_contrib_drivers.drivers.QuTech.IVVI_Modules import (
    IVVI_Module, S4c, M2m, M2b, M1b, VId, IVd
)


@pytest.fixture(scope="function", name="base_module")
def _make_base_module():
    """Create a base IVVI module for testing."""
    module = IVVI_Module("test_base")
    yield module
    module.close()


@pytest.fixture(scope="function", name="s4c")
def _make_s4c():
    """Create an S4c current source module for testing."""
    module = S4c("test_s4c")
    yield module
    module.close()


@pytest.fixture(scope="function", name="m2m")
def _make_m2m():
    """Create an M2m voltage source module for testing."""
    module = M2m("test_m2m")
    yield module
    module.close()


@pytest.fixture(scope="function", name="m2b")
def _make_m2b():
    """Create an M2b voltage source module for testing."""
    module = M2b("test_m2b")
    yield module
    module.close()


@pytest.fixture(scope="function", name="m1b")
def _make_m1b():
    """Create an M1b voltage source module for testing."""
    module = M1b("test_m1b")
    yield module
    module.close()


@pytest.fixture(scope="function", name="vid")
def _make_vid():
    """Create a VId voltage measurement module for testing."""
    module = VId("test_vid", num_channels=4)
    yield module
    module.close()


@pytest.fixture(scope="function", name="ivd")
def _make_ivd():
    """Create an IVd source-measure module for testing."""
    module = IVd("test_ivd", num_channels=2)
    yield module
    module.close()


def test_base_module_idn(base_module) -> None:
    """Test the base module IDN functionality."""
    idn = base_module.get_idn()
    expected_keys = {"vendor", "model", "serial", "firmware"}
    assert expected_keys == set(idn.keys())
    assert idn["vendor"] == "QuTech"
    assert "IVVI" in idn["model"]
    assert idn["serial"] == "Manual"
    assert idn["firmware"] == "N/A"


def test_base_module_parameters(base_module) -> None:
    """Test base module common parameters."""
    # Test setting and getting common parameters
    base_module.module_type("TestType")
    base_module.rack_position("Slot 1")
    base_module.notes("Test notes")
    
    assert base_module.module_type() == "TestType"
    assert base_module.rack_position() == "Slot 1"
    assert base_module.notes() == "Test notes"


def test_s4c_initialization(s4c) -> None:
    """Test S4c current source initialization."""
    assert s4c.name == "test_s4c"
    assert s4c.module_type() == "S4c"
    assert s4c.current_range() == "±2mA"


def test_s4c_channels_and_parameters(s4c) -> None:
    """Test S4c channel parameters."""
    # Check that all 4 channels exist
    for i in range(1, 5):
        assert hasattr(s4c, f"ch{i}_current")
        assert hasattr(s4c, f"ch{i}_enabled")
        
        # Test initial values
        assert s4c.parameters[f"ch{i}_current"]() == 0.0
        assert s4c.parameters[f"ch{i}_enabled"]() is False


def test_s4c_current_setting_and_validation(s4c) -> None:
    """Test S4c current setting and validation."""
    # Test valid current setting
    s4c.ch1_current(1e-3)  # 1 mA
    assert s4c.ch1_current() == 1e-3
    
    # Test boundary values
    s4c.ch1_current(2e-3)   # +2 mA (max)
    s4c.ch1_current(-2e-3)  # -2 mA (min)
    
    # Test invalid values should raise
    with pytest.raises(ValueError):
        s4c.ch1_current(3e-3)  # Too high
    with pytest.raises(ValueError):
        s4c.ch1_current(-3e-3)  # Too low


def test_s4c_specifications(s4c) -> None:
    """Test S4c specifications and resolution."""
    resolution = s4c.resolution()
    expected_resolution = (2 * 2e-3) / (2**12)  # 4mA / 4096
    assert abs(resolution - expected_resolution) < 1e-12
    
    assert s4c.compliance_voltage() == 10.0


def test_m2m_initialization(m2m) -> None:
    """Test M2m voltage source initialization."""
    assert m2m.name == "test_m2m"
    assert m2m.module_type() == "M2m"
    assert m2m.voltage_range() == "±4V"


def test_m2m_channels_and_parameters(m2m) -> None:
    """Test M2m channel parameters."""
    # Check that 2 channels exist
    for i in range(1, 3):
        assert hasattr(m2m, f"ch{i}_voltage")
        assert hasattr(m2m, f"ch{i}_enabled")
        
        # Test initial values
        assert m2m.parameters[f"ch{i}_voltage"]() == 0.0
        assert m2m.parameters[f"ch{i}_enabled"]() is False


def test_m2m_voltage_setting_and_validation(m2m) -> None:
    """Test M2m voltage setting and validation."""
    # Test valid voltage setting
    m2m.ch1_voltage(2.5)  # 2.5 V
    assert m2m.ch1_voltage() == 2.5
    
    # Test boundary values
    m2m.ch1_voltage(4.0)   # +4V (max)
    m2m.ch1_voltage(-4.0)  # -4V (min)
    
    # Test invalid values should raise
    with pytest.raises(ValueError):
        m2m.ch1_voltage(5.0)  # Too high
    with pytest.raises(ValueError):
        m2m.ch1_voltage(-5.0)  # Too low


def test_m2m_specifications(m2m) -> None:
    """Test M2m specifications."""
    resolution = m2m.resolution()
    expected_resolution = (2 * 4.0) / (2**16)  # 8V / 65536
    assert abs(resolution - expected_resolution) < 1e-12
    
    assert m2m.max_current() == 10e-3  # 10 mA


def test_m2b_initialization(m2b) -> None:
    """Test M2b voltage source initialization."""
    assert m2b.name == "test_m2b"
    assert m2b.module_type() == "M2b"
    assert m2b.voltage_range() == "±10V"


def test_m2b_different_from_m2m(m2b, m2m) -> None:
    """Test that M2b has different specifications from M2m."""
    # M2b should have ±10V range vs M2m ±4V
    assert m2b.voltage_range() == "±10V"
    assert m2m.voltage_range() == "±4V"
    
    # M2b should have 2mA max current vs M2m 10mA
    assert m2b.max_current() == 2e-3
    assert m2m.max_current() == 10e-3


def test_m1b_initialization(m1b) -> None:
    """Test M1b voltage source initialization."""
    assert m1b.name == "test_m1b"
    assert m1b.module_type() == "M1b"
    assert m1b.voltage_range() == "±10V"


def test_m1b_single_channel(m1b) -> None:
    """Test that M1b has only one channel."""
    # Should have channel 1
    assert hasattr(m1b, "ch1_voltage")
    assert hasattr(m1b, "ch1_enabled")
    
    # Should not have channel 2
    assert not hasattr(m1b, "ch2_voltage")
    assert not hasattr(m1b, "ch2_enabled")


def test_vid_initialization(vid) -> None:
    """Test VId voltage measurement initialization."""
    assert vid.name == "test_vid"
    assert vid.module_type() == "VId"
    assert vid.measurement_range() == "±10V"
    assert vid.num_channels() == 4


def test_vid_channels_and_parameters(vid) -> None:
    """Test VId measurement channel parameters."""
    # Check that 4 channels exist
    for i in range(1, 5):
        assert hasattr(vid, f"ch{i}_voltage")
        assert hasattr(vid, f"ch{i}_enabled")
        
        # Test initial values (measurements default to enabled)
        assert vid.parameters[f"ch{i}_voltage"]() == 0.0
        assert vid.parameters[f"ch{i}_enabled"]() is True


def test_vid_specifications(vid) -> None:
    """Test VId specifications."""
    assert vid.input_impedance() == 1e12  # >10^12 Ω
    assert vid.bandwidth() == 1000  # 1 kHz
    assert vid.accuracy() == 0.001  # ±0.1%
    
    resolution = vid.resolution()
    expected_resolution = (2 * 10.0) / (2**16)  # 20V / 65536
    assert abs(resolution - expected_resolution) < 1e-12


def test_ivd_initialization(ivd) -> None:
    """Test IVd source-measure initialization."""
    assert ivd.name == "test_ivd"
    assert ivd.module_type() == "IVd"
    assert ivd.voltage_range() == "±4V"
    assert ivd.current_range() == "±1uA"
    assert ivd.num_channels() == 2


def test_ivd_source_measure_parameters(ivd) -> None:
    """Test IVd source and measure parameters."""
    # Check that each channel has both source and measure parameters
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


def test_ivd_voltage_and_current_validation(ivd) -> None:
    """Test IVd voltage and current validation."""
    # Test voltage source validation
    ivd.ch1_voltage(2.0)  # 2V
    assert ivd.ch1_voltage() == 2.0
    
    with pytest.raises(ValueError):
        ivd.ch1_voltage(5.0)  # Too high for ±4V range
    
    # Test current measurement validation
    ivd.ch1_current(0.5e-6)  # 0.5 μA
    assert ivd.ch1_current() == 0.5e-6
    
    with pytest.raises(ValueError):
        ivd.ch1_current(2e-6)  # Too high for ±1μA range


def test_ivd_specifications(ivd) -> None:
    """Test IVd specifications."""
    assert ivd.source_accuracy() == 0.001  # ±0.1%
    assert ivd.measure_accuracy() == 0.001  # ±0.1%
    
    v_res = ivd.voltage_resolution()
    expected_v = (2 * 4.0) / (2**16)  # 8V / 65536
    assert abs(v_res - expected_v) < 1e-12
    
    i_res = ivd.current_resolution()
    expected_i = (2 * 1e-6) / (2**16)  # 2μA / 65536
    assert abs(i_res - expected_i) < 1e-12


def test_module_snapshots(s4c, m2m, vid, ivd) -> None:
    """Test that modules can take snapshots."""
    modules = [s4c, m2m, vid, ivd]
    
    for module in modules:
        # Configure some parameters
        module.rack_position("Test Slot")
        module.notes("Test configuration")
        
        # Take snapshot
        snapshot = module.snapshot()
        
        # Verify snapshot structure
        assert "parameters" in snapshot
        assert "module_type" in snapshot["parameters"]
        assert "rack_position" in snapshot["parameters"]
        assert "notes" in snapshot["parameters"]


def test_multiple_module_instantiation() -> None:
    """Test creating multiple modules simultaneously."""
    try:
        modules = {
            "s4c": S4c("current_source"),
            "m2m": M2m("voltage_source_1"),
            "m2b": M2b("voltage_source_2"),
            "m1b": M1b("single_voltage"),
            "vid": VId("voltmeter", num_channels=6),
            "ivd": IVd("source_measure", num_channels=3),
        }
        
        # All should be properly initialized
        for name, module in modules.items():
            assert module.name == module.name
            idn = module.get_idn()
            assert "IVVI" in idn["model"]
            assert idn["vendor"] == "QuTech"
        
    finally:
        # Clean up
        for module in modules.values():
            module.close()


def test_module_configuration_example() -> None:
    """Test a realistic module configuration scenario."""
    try:
        # Create modules for a typical measurement setup
        current_source = S4c("gate_cs")
        voltage_source = M2m("bias_vs")
        voltmeter = VId("monitor_vm", num_channels=4)
        smu = IVd("current_smu", num_channels=2)
        
        # Configure rack positions
        current_source.rack_position("Slot 1")
        voltage_source.rack_position("Slot 2")
        voltmeter.rack_position("Slot 3")
        smu.rack_position("Slot 4")
        
        # Set some typical values
        current_source.ch1_enabled(True)
        current_source.ch1_current(1e-3)  # 1 mA
        
        voltage_source.ch1_enabled(True)
        voltage_source.ch1_voltage(2.5)   # 2.5 V
        
        smu.ch1_source_enabled(True)
        smu.ch1_voltage(1.0)              # 1.0 V
        smu.ch1_current(0.5e-6)           # 0.5 μA measured
        
        # Verify configuration
        assert current_source.rack_position() == "Slot 1"
        assert current_source.ch1_current() == 1e-3
        assert voltage_source.ch1_voltage() == 2.5
        assert smu.ch1_voltage() == 1.0
        assert smu.ch1_current() == 0.5e-6
        
    finally:
        # Clean up
        for module in [current_source, voltage_source, voltmeter, smu]:
            module.close()