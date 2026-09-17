"""
Tests for the Kiutra L-Type Rapid cryostat driver.

This file holds two kinds of test. The validator tests are pure unit tests and
always run. The tests taking the ``driver`` fixture open a connection to a real
L-Type Rapid, and some of them start temperature and field ramps on it, so they
are skipped by default and only run when hardware testing is opted in::

    pytest tests/Kiutra                                    # validators only
    KIUTRA_HARDWARE_TESTS=1 KIUTRA_ADDRESS=<ip> pytest tests/Kiutra

Do not opt in against a cold system unless you mean to warm it up: the tests
ramp the temperature to 20 K, which dumps the ADR. See conftest.py for the
guard that enforces this and for the environment variables it reads.
"""

import pytest
import numpy as np

from qcodes_contrib_drivers.drivers.Kiutra.L_Type_Rapid import (
    LTypeRapid,
    TemperatureChannel,
    MagnetChannel,
    ADRRampValidator,
)
from qcodes.validators import Numbers, Enum
from qcodes.parameters import Parameter


@pytest.fixture(scope="function", name="driver")
def _make_driver(kiutra_address, kiutra_port):
    """
    Create a Kiutra L-Type Rapid driver for testing.

    This talks to a real system. Tests using it are skipped unless hardware
    testing is opted in; see conftest.py for the environment variables that
    select the address and enable these tests.
    """
    driver = LTypeRapid(
        "kiutra_ltype_rapid",
        address=kiutra_address,
        port=kiutra_port,
    )
    yield driver
    # Cleanup: stop any running operations
    try:
        driver.temperature_control.controller.stop()
    except Exception:
        pass
    driver.close()


@pytest.fixture(name="temp_parameter")
def _make_temp_parameter():
    """Create a simple parameter for testing ADRRampValidator."""
    param = Parameter(
        "test_temp",
        vals=Numbers(0.083, 300.0),
        get_cmd=None,
        set_cmd=None,
        initial_value=10.0
    )
    return param


class TestADRRampValidator:
    """Test the ADRRampValidator functionality without hardware."""

    def test_validator_initialization(self, temp_parameter):
        """Test that ADRRampValidator initializes correctly."""
        ramp_limits = [
            (0.083, 1.0, 0.5),
            (1.0, 5.0, 1.0),
            (5.0, 20.0, 2.0),
        ]

        validator = ADRRampValidator(ramp_limits, temp_parameter)
        assert validator._ramp_limits == ramp_limits
        assert validator._temperature_setpoint == temp_parameter

    def test_validator_rejects_non_numbers(self, temp_parameter):
        """Test that validator rejects non-numeric values."""
        ramp_limits = [(1.0, 10.0, 1.0)]
        validator = ADRRampValidator(ramp_limits, temp_parameter)

        with pytest.raises(TypeError, match="is not an int or float"):
            validator.validate("not a number")

        with pytest.raises(TypeError, match="is not an int or float"):
            validator.validate(None)

    def test_validator_with_setpoint_below_minimum(self, temp_parameter):
        """Test validation when setpoint is below minimum ramp limit."""
        ramp_limits = [(0.083, 1.0, 0.5)]
        validator = ADRRampValidator(ramp_limits, temp_parameter)
        
        # Set setpoint below minimum (bypass parameter's own validator)
        temp_parameter.cache._set_from_raw_value(0.05)

        with pytest.raises(ValueError, match="below the minimum ramp limit"):
            validator.validate(0.3)

    def test_validator_with_empty_ramp_limits(self, temp_parameter):
        """Test validation when ramp_limits is empty."""
        ramp_limits = []
        validator = ADRRampValidator(ramp_limits, temp_parameter)

        with pytest.raises(ValueError, match="Ramp limits not available"):
            validator.validate(0.5)

    def test_validator_accepts_valid_ramps_in_range(self, temp_parameter):
        """Test that validator accepts valid ramp rates for each temperature range."""
        ramp_limits = [
            (0.083, 1.0, 0.5),
            (1.0, 5.0, 1.0),
            (5.0, 20.0, 2.0),
        ]
        validator = ADRRampValidator(ramp_limits, temp_parameter)

        # Test valid ramps in first range
        temp_parameter.set(0.5)
        validator.validate(0.0)
        validator.validate(0.3)
        validator.validate(0.5)

        # Test valid ramps in second range
        temp_parameter.set(3.0)
        validator.validate(0.0)
        validator.validate(0.5)
        validator.validate(1.0)

        # Test valid ramps in third range
        temp_parameter.set(10.0)
        validator.validate(0.0)
        validator.validate(1.0)
        validator.validate(2.0)

    def test_validator_rejects_excessive_ramps(self, temp_parameter):
        """Test that validator rejects ramp rates above the limit for each range."""
        ramp_limits = [
            (0.083, 1.0, 0.5),
            (1.0, 5.0, 1.0),
            (5.0, 20.0, 2.0),
        ]
        validator = ADRRampValidator(ramp_limits, temp_parameter)

        # Test excessive ramp in first range
        temp_parameter.set(0.5)
        with pytest.raises(ValueError, match="out of bounds"):
            validator.validate(0.51)
        with pytest.raises(ValueError, match="out of bounds"):
            validator.validate(0.6)

        # Test excessive ramp in second range
        temp_parameter.set(3.0)
        with pytest.raises(ValueError, match="out of bounds"):
            validator.validate(1.01)
        with pytest.raises(ValueError, match="out of bounds"):
            validator.validate(1.1)

        # Test excessive ramp in third range
        temp_parameter.set(10.0)
        with pytest.raises(ValueError, match="out of bounds"):
            validator.validate(2.01)
        with pytest.raises(ValueError, match="out of bounds"):
            validator.validate(2.1)

    def test_validator_at_range_boundaries(self, temp_parameter):
        """Test validator behavior at temperature range boundaries."""
        ramp_limits = [
            (0.083, 1.0, 0.5),
            (1.0, 5.0, 1.0),
            (5.0, 20.0, 2.0),
        ]
        validator = ADRRampValidator(ramp_limits, temp_parameter)

        # At lower boundary of first range
        temp_parameter.set(0.083)
        validator.validate(0.5)

        # At boundary between first and second range the higher limit applies,
        # up to and including it.
        temp_parameter.set(1.0)
        validator.validate(1.0)
        with pytest.raises(ValueError, match="out of bounds"):
            validator.validate(1.01)

        # At boundary between second and third range
        temp_parameter.set(5.0)
        validator.validate(2.0)
        with pytest.raises(ValueError, match="out of bounds"):
            validator.validate(2.01)

    def test_validator_above_all_ranges(self, temp_parameter):
        """Test validator when setpoint is above all defined ranges."""
        ramp_limits = [
            (0.083, 1.0, 0.5),
            (1.0, 5.0, 1.0),
            (5.0, 20.0, 2.0),
        ]
        validator = ADRRampValidator(ramp_limits, temp_parameter)

        # Setpoint above all ranges - should use maximum ramp of 2.0 K/min
        temp_parameter.set(50.0)
        validator.validate(0.5)
        validator.validate(1.5)
        validator.validate(2.0)

        # Should reject ramps above absolute maximum
        with pytest.raises(ValueError, match="out of bounds"):
            validator.validate(2.1)

    def test_validator_with_negative_ramps(self, temp_parameter):
        """Test that validator rejects negative ramp rates."""
        ramp_limits = [(1.0, 10.0, 1.0)]
        validator = ADRRampValidator(ramp_limits, temp_parameter)
        temp_parameter.set(5.0)

        with pytest.raises(ValueError, match="out of bounds"):
            validator.validate(-0.1)

    def test_validator_requires_numbers_validator(self):
        """Test that validator requires temperature parameter with Numbers validator."""
        temp_param = Parameter(
            "test_temp",
            vals=Enum("low", "high"),  # Not a Numbers validator
            get_cmd=None,
            set_cmd=None
        )

        ramp_limits = [(1.0, 10.0, 1.0)]

        with pytest.raises(TypeError, match="Temperature_setpoint must have vals of type Numbers"):
            ADRRampValidator(ramp_limits, temp_param)

    def test_validator_requires_vals_on_setpoint(self):
        """Test that a setpoint parameter without any validator is rejected."""
        temp_param = Parameter(
            "test_no_vals",
            get_cmd=None,
            set_cmd=None,
            initial_value=10.0,
        )

        ramp_limits = [(1.0, 10.0, 1.0)]

        with pytest.raises(TypeError, match="Temperature_setpoint must have vals of type Numbers"):
            ADRRampValidator(ramp_limits, temp_param)

    def test_validator_with_numpy_types(self, temp_parameter):
        """Test that validator accepts numpy numeric types."""
        ramp_limits = [(1.0, 10.0, 1.0)]
        validator = ADRRampValidator(ramp_limits, temp_parameter)
        temp_parameter.set(5.0)

        # Test with numpy types
        validator.validate(np.float64(0.5))
        validator.validate(np.float32(0.7))
        validator.validate(np.int32(0))
        validator.validate(np.int64(1))


class TestParameterValidators:
    """Test parameter validators without requiring hardware."""

    def test_temperature_validator_ranges(self):
        """Test that temperature validator has correct range."""
        validator = Numbers(0.083, 300.0)
        
        # Valid temperatures
        validator.validate(0.083)
        validator.validate(1.0)
        validator.validate(100.0)
        validator.validate(300.0)
        
        # Invalid temperatures
        with pytest.raises(ValueError):
            validator.validate(-1.0)
        with pytest.raises(ValueError):
            validator.validate(0.082)
        with pytest.raises(ValueError):
            validator.validate(300.1)
        with pytest.raises(ValueError):
            validator.validate(500.0)

    def test_ramp_rate_validator_ranges(self):
        """Test that ramp rate validator has correct range."""
        validator = Numbers(0, 5.0)
        
        # Valid ramp rates
        validator.validate(0.0)
        validator.validate(0.5)
        validator.validate(2.5)
        validator.validate(5.0)
        
        # Invalid ramp rates
        with pytest.raises(ValueError):
            validator.validate(-0.1)
        with pytest.raises(ValueError):
            validator.validate(5.1)
        with pytest.raises(ValueError):
            validator.validate(10.0)

    def test_field_validator_ranges(self):
        """Test that magnetic field validator has correct range."""
        validator = Numbers(-5.5, 5.5)

        # Valid fields
        validator.validate(-5.5)
        validator.validate(-2.5)
        validator.validate(0.0)
        validator.validate(2.5)
        validator.validate(5.5)

        # Invalid fields
        with pytest.raises(ValueError):
            validator.validate(-5.6)
        with pytest.raises(ValueError):
            validator.validate(5.6)

    def test_magnet_ramp_validator_ranges(self):
        """Test that magnet ramp validator has correct range."""
        validator = Numbers(0, 0.5)
        
        # Valid ramp rates
        validator.validate(0.0)
        validator.validate(0.1)
        validator.validate(0.25)
        validator.validate(0.5)
        
        # Invalid ramp rates
        with pytest.raises(ValueError):
            validator.validate(-0.1)
        with pytest.raises(ValueError):
            validator.validate(0.51)
        with pytest.raises(ValueError):
            validator.validate(1.0)

    def test_operation_mode_validator(self):
        """Test that operation mode validator accepts correct values."""
        validator = Enum("adr", "cadr", "universal", "heater")
        
        # Valid modes
        validator.validate("adr")
        validator.validate("cadr")
        validator.validate("universal")
        validator.validate("heater")
        
        # Invalid mode
        with pytest.raises(ValueError):
            validator.validate("invalid_mode")


def test_instrument_creation(driver) -> None:
    """Test that the instrument is created with correct attributes."""
    assert driver.name == "kiutra_ltype_rapid"
    assert driver._address is not None
    assert driver._port is not None


def test_submodules_exist(driver) -> None:
    """Test that all expected submodules are created."""
    assert hasattr(driver, "temperature_control")
    assert hasattr(driver, "magnet_control")
    assert isinstance(driver.temperature_control, TemperatureChannel)
    assert isinstance(driver.magnet_control, MagnetChannel)


def test_temperature_parameter_exists(driver) -> None:
    """Test that temperature parameter is properly configured."""
    temp_channel = driver.temperature_control
    assert hasattr(temp_channel, "temperature")
    assert temp_channel.temperature.unit == "K"
    assert temp_channel.temperature.label == "Temperature"


def test_temperature_get(driver) -> None:
    """Test reading current temperature."""
    temp_channel = driver.temperature_control
    temp = temp_channel.temperature()

    assert isinstance(temp, (float, int, np.floating, np.integer))
    # Should return reasonable values
    assert 0.08 <= temp <= 301.0


def test_temperature_setpoint_get_set(driver) -> None:
    """Test getting and setting temperature setpoint."""
    temp_channel = driver.temperature_control

    original_setpoint = temp_channel.temperature_setpoint()
    test_setpoint = 10.0
    temp_channel.temperature_setpoint(test_setpoint)
    assert abs(temp_channel.temperature_setpoint() - test_setpoint) < 0.001

    # Restore original setpoint
    temp_channel.temperature_setpoint(original_setpoint)


def test_temperature_setpoint_validation(driver) -> None:
    """Test that temperature setpoint validates correctly."""
    temp_channel = driver.temperature_control

    # Valid temperatures
    valid_temps = [0.083, 1.0, 10.0, 50.0, 100.0, 300.0]
    for temp in valid_temps:
        temp_channel.temperature_setpoint.validate(temp)

    # Invalid temperatures
    invalid_temps = [-1.0, 0.0, 0.082, 300.1, 500.0]
    for temp in invalid_temps:
        with pytest.raises(ValueError):
            temp_channel.temperature_setpoint.validate(temp)


def test_ramp_rate_get_set(driver) -> None:
    """Test getting and setting ramp rate."""
    temp_channel = driver.temperature_control

    original_ramp = temp_channel.ramp()
    test_ramp = 0.5
    temp_channel.ramp(test_ramp)
    assert abs(temp_channel.ramp() - test_ramp) < 0.001

    # Restore original ramp
    temp_channel.ramp(original_ramp)


def test_ramp_rate_validation(driver) -> None:
    """Test that ramp rate validates correctly."""
    temp_channel = driver.temperature_control

    # Valid ramp rates
    valid_ramps = [0.0, 0.5, 1.0, 2.5, 5.0]
    for ramp in valid_ramps:
        temp_channel.ramp.validate(ramp)

    # Invalid ramp rates
    invalid_ramps = [-0.1, 5.1, 10.0]
    for ramp in invalid_ramps:
        with pytest.raises(ValueError):
            temp_channel.ramp.validate(ramp)


def test_operation_modes(driver) -> None:
    """Test that all operation modes are available and can be set."""
    temp_channel = driver.temperature_control
    valid_modes = ["adr", "cadr", "universal", "heater"]

    for mode in valid_modes:
        temp_channel.operation_mode(mode)
        assert temp_channel.operation_mode() == mode

    # Invalid mode
    with pytest.raises(ValueError):
        temp_channel.operation_mode("invalid_mode")


def test_temperature_control_starts(driver) -> None:
    """Test that setting temperature starts control with correct parameters."""
    temp_channel = driver.temperature_control

    # Configure control parameters
    temp_channel.ramp(1.0)
    temp_channel.operation_mode("universal")

    # Start temperature control
    temp_channel.temperature(20.0)

    # Verify setpoint and ramp were updated
    assert temp_channel.temperature_setpoint() == 20.0
    assert temp_channel.ramp() == 1.0

    # Verify status changed to ramping (210=initializing, 220=ramping)
    status = temp_channel.controller.query_value("status")
    assert status[0] in [210, 220]  # Initializing or ramping status code
    assert isinstance(status[1], str)  # Status message exists


def test_temperature_stop(driver) -> None:
    """Test that stopping temperature control works."""
    temp_channel = driver.temperature_control

    # Start control
    initial_temp = temp_channel.temperature()
    temp_channel.temperature(initial_temp + 10.0)
    status_ramping = temp_channel.controller.query_value("status")
    assert status_ramping[0] == 220  # Should be ramping

    # Stop control
    temp_channel.controller.stop()
    status_stopped = temp_channel.controller.query_value("status")
    assert status_stopped[0] == 200
    assert status_stopped[1] == ""


def test_magnet_parameter_exists(driver) -> None:
    """Test that magnet field parameter is properly configured."""
    magnet_channel = driver.magnet_control
    assert hasattr(magnet_channel, "field")
    assert magnet_channel.field.unit == "T"
    assert magnet_channel.field.label == "Magnetic Field"


def test_field_get(driver) -> None:
    """Test reading current magnetic field."""
    magnet_channel = driver.magnet_control
    field = magnet_channel.field()

    assert isinstance(field, (float, int, np.floating, np.integer))
    # Should return reasonable values
    assert -5.6 <= field <= 5.6


def test_field_setpoint_get_set(driver) -> None:
    """Test getting and setting field setpoint."""
    magnet_channel = driver.magnet_control

    original_setpoint = magnet_channel.field_setpoint()
    test_setpoint = 0.5
    magnet_channel.field_setpoint(test_setpoint)
    assert abs(magnet_channel.field_setpoint() - test_setpoint) < 0.001

    # Restore original setpoint
    magnet_channel.field_setpoint(original_setpoint)


def test_field_validation(driver) -> None:
    """Test that magnetic field validates correctly."""
    magnet_channel = driver.magnet_control

    # Valid fields
    valid_fields = [-5.5, -2.5, 0.0, 2.5, 5.5]
    for field in valid_fields:
        magnet_channel.field_setpoint.validate(field)

    # Invalid fields
    invalid_fields = [-5.6, -6.0, 5.6, 10.0]
    for field in invalid_fields:
        with pytest.raises(ValueError):
            magnet_channel.field_setpoint.validate(field)


def test_magnet_ramp_get_set(driver) -> None:
    """Test getting and setting magnet ramp rate."""
    magnet_channel = driver.magnet_control

    original_ramp = magnet_channel.ramp()
    test_ramp = 0.2
    magnet_channel.ramp(test_ramp)
    assert abs(magnet_channel.ramp() - test_ramp) < 0.001

    # Restore original ramp
    magnet_channel.ramp(original_ramp)


def test_magnet_ramp_validation(driver) -> None:
    """Test that magnet ramp rate validates correctly."""
    magnet_channel = driver.magnet_control

    # Valid ramp rates
    valid_ramps = [0.0, 0.1, 0.25, 0.5]
    for ramp in valid_ramps:
        magnet_channel.ramp.validate(ramp)

    # Invalid ramp rates
    invalid_ramps = [-0.1, 0.51, 1.0]
    for ramp in invalid_ramps:
        with pytest.raises(ValueError):
            magnet_channel.ramp.validate(ramp)


def test_magnet_ramp_starts(driver) -> None:
    """Test that setting field starts ramping with correct parameters."""
    magnet_channel = driver.magnet_control

    # Configure ramp
    magnet_channel.ramp(0.2)

    # Start ramping
    magnet_channel.field(2.0)

    # Verify setpoint and ramp were set correctly
    assert magnet_channel.field_setpoint() == 2.0
    assert abs(magnet_channel.ramp() - 0.2) < 0.01  # Allow for floating point precision


def test_parameter_persistence(driver) -> None:
    """Test that set values persist in the controller."""
    temp_channel = driver.temperature_control

    # Set multiple parameters
    temp_channel.temperature_setpoint(25.0)
    temp_channel.ramp(1.5)
    temp_channel.operation_mode("cadr")

    # Verify persistence
    assert temp_channel.temperature_setpoint() == 25.0
    assert temp_channel.ramp() == 1.5
    assert temp_channel.operation_mode() == "cadr"


def test_query_adr_ramp_limits(driver) -> None:
    """Test querying ADR ramp limits."""
    try:
        from kiutra_api.controller_interfaces import ADRControl
    except ImportError:
        pytest.skip("kiutra_api not available")

    adr_controller = ADRControl("adr_control", driver._address, driver._port)
    ramp_limits = adr_controller.query_value("ramp_limits")

    assert isinstance(ramp_limits, list)
    assert len(ramp_limits) > 0

    # Verify structure of ramp limits (can be tuple or list depending on mock vs real API)
    for limit in ramp_limits:
        assert isinstance(limit, (tuple, list))
        assert len(limit) == 3
        min_temp, max_temp, max_ramp = limit
        assert min_temp < max_temp
        assert max_ramp > 0


def test_temperature_status_query(driver) -> None:
    """Test querying temperature control status."""
    temp_channel = driver.temperature_control
    status = temp_channel.controller.query_value("status")

    assert isinstance(status, list)
    assert len(status) == 2
    assert isinstance(status[0], int)
    assert isinstance(status[1], str)


def test_connection_to_controllers(driver) -> None:
    """Test that we can connect to the Kiutra device controllers."""
    assert driver.temperature_control.controller is not None
    assert driver.magnet_control.controller is not None


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
