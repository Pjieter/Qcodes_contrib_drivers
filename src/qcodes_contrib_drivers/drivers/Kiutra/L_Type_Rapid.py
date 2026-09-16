from typing import TYPE_CHECKING, Optional
from collections.abc import Callable
import logging
import time

import numpy as np
from qcodes.instrument import Instrument, InstrumentBaseKWArgs, InstrumentChannel
from qcodes.parameters import ManualParameter, Parameter
from qcodes.validators import Enum, Numbers, Validator
from kiutra_api.controller_interfaces import (  # type: ignore
    TemperatureControl,
    MagnetControl,
    ADRControl,
    HeaterControl,
)
from kiutra_api.api_client import KiutraClient  # type: ignore

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from typing_extensions import Unpack

numbertypes = float | int | np.floating | np.integer


class ADRRampValidator(Validator[numbertypes]):
    """
    Requires a number of type int, float, numpy.integer or numpy.floating.
    Depends on the ramp limits set in the ADR controller.

    Args:
        ramp_limits: The ramp rate limits list.
        temperature_setpoint_getter: The current temperature setpoint getter.

    """

    is_numeric = True

    def __init__(
        self,
        ramp_limits: list[tuple[numbertypes, numbertypes, numbertypes]],
        temperature_setpoint: Parameter,
    ) -> None:
        """Initializes the ADRRampValidator."""
        self._ramp_limits = ramp_limits
        self._temperature_setpoint = temperature_setpoint
        # Make sure the temperature_setpoint has vals of type Numbers
        if not isinstance(self._temperature_setpoint.vals, Numbers):
            raise TypeError("Temperature_setpoint must have vals of type Numbers")
        self.temperature_validator = self._temperature_setpoint.vals
        # Initialize to avoid attribute error, set to proper values in validate.
        self._valid_values = (0, 0)
        self._maximum_ramp = 2.0  # The absolute maximum ramp rate for ADRs

    def validate(self, value: numbertypes, context: str = "") -> None:
        """
        Validates the ramp rate for the ADR.

        The validation depends on the current temperature setpoint, as the allowed
        ramp rates change with temperature.

        Args:
            value: The ramp rate value to validate.
            context: A string providing context for the validation.

        Raises:
            TypeError: If the value is not a valid number.
            ValueError: If the ramp rate is outside the allowed range for the
                current setpoint.
        """

        if not isinstance(value, (int, float, np.integer, np.floating)):
            raise TypeError(f"{value!r} is not an int or float; {context}")

        # Check for empty ramp_limits
        if not self._ramp_limits:
            raise ValueError(
                f"Ramp limits not available from controller; cannot validate ramp rate; {context}"
            )

        # Compute min and max temperature bounds from ramp_limits
        # The list may not be ordered, so find the actual min/max across all intervals
        min_temp = min(interval[0] for interval in self._ramp_limits)
        max_temp = max(interval[1] for interval in self._ramp_limits)

        setpoint = self._temperature_setpoint()

        # Check if setpoint is below the minimum covered temperature
        if setpoint < min_temp:
            raise ValueError(
                f"Setpoint {setpoint} K is below the minimum ramp limit (starts at {min_temp} K); {context}"
            )

        # Check each interval to find the matching one
        for temp_min, temp_max, ramp_max in self._ramp_limits:
            if temp_min <= setpoint < temp_max:
                self._valid_values = (0, ramp_max)
                if not (0 <= value <= ramp_max):
                    raise ValueError(
                        f"Ramp rate {value} K/min is out of bounds for setpoint {setpoint} K. "
                        f"Valid range is 0 to {ramp_max} K/min.; {context}"
                    )
                return

        # Handle setpoints at or above the last interval's upper bound
        if max_temp <= setpoint <= self.temperature_validator.max_value:
            self._valid_values = (0, self._maximum_ramp)
            if not (0 <= value <= self._maximum_ramp):
                raise ValueError(
                    f"Ramp rate {value} K/min is out of bounds for setpoint {setpoint} K. "
                    f"Valid range is 0 to {self._maximum_ramp} K/min.; {context}"
                )
            return

        # If we reach here, setpoint falls in a gap between intervals
        raise ValueError(f"Setpoint {setpoint} K is outside all ramp limits; {context}")


class TemperatureChannel(InstrumentChannel):
    """
    QCoDeS driver for a temperature channel of the Kiutra L-Type Rapid cryostat.

    Args:
        parent: The parent instrument (LTypeRapid).
        name: The name of the temperature channel.
    """

    controller: TemperatureControl
    adr_controller: ADRControl

    def __init__(
        self,
        parent: "LTypeRapid",
        name: str,
    ) -> None:
        super().__init__(parent, name)

        self._connect_temperature_controller()
        self._connect_adr_controller()
        self.temperature_validator = Numbers(0.083, 300.0)

        self.temperature = self.add_parameter(
            "temperature",
            label="Temperature",
            unit="K",
            get_cmd=lambda: self.controller.kelvin,
            set_cmd=self._set_temperature,
            vals=self.temperature_validator,
        )
        """Parameter temperature"""

        self.ramp: Parameter = self.add_parameter(
            "ramp",
            label="Temperature ramp rate",
            unit="K/min",
            get_cmd=lambda: self.controller.ramp,
            set_cmd=lambda value: self.controller.set_value("ramp", value),
            vals=Numbers(0, 2.0),
        )
        """Parameter ramp"""

        self.operation_mode: ManualParameter = self.add_parameter(
            "operation_mode",
            parameter_class=ManualParameter,
            label="Temperature Operation Mode",
            initial_value="universal",
            unit=None,
            vals=Enum("adr", "cadr", "universal", "heater"),
            docstring="Sets the operation mode of the temperature controller. Options are 'adr', 'cadr', 'universal', and 'heater'.",
        )

        self.temperature_setpoint: Parameter = self.add_parameter(
            "temperature_setpoint",
            label="Temperature setpoint",
            unit="K",
            get_cmd=lambda: self.controller.setpoint,
            set_cmd=lambda value: self.controller.set_value("setpoint", value),
            vals=self.temperature_validator,
        )
        """Parameter temperature_setpoint"""

        self.blocking: ManualParameter = self.add_parameter(
            "blocking",
            parameter_class=ManualParameter,
            label="Blocking mode for temperature setting",
            initial_value=True,
            vals=Enum(True, False),
            docstring="If True, temperature setter waits for stabilization. If False, returns immediately.",
        )
        """Parameter blocking"""

        self.timeout: ManualParameter = self.add_parameter(
            "timeout",
            parameter_class=ManualParameter,
            label="Timeout for temperature stabilization",
            unit="s",
            initial_value=3600.0,
            vals=Numbers(0, float('inf')),
            docstring="Maximum time to wait for temperature stabilization in seconds.",
        )
        """Parameter timeout"""

        self.status: Parameter = self.add_parameter(
            "status",
            label="Temperature controller status",
            get_cmd=lambda: self.controller.query_value('status'),
            docstring="Current status of the temperature controller as (status_code, status_message).",
        )
        """Parameter status"""

        self.stable: Parameter = self.add_parameter(
            "stable",
            label="Temperature stability status",
            get_cmd=lambda: self.controller.query_value('status')[0] == 200,
            docstring="True if the temperature controller is in a stable state (status is 200).",
        )
        """Parameter stable"""

    def _connect_temperature_controller(self) -> KiutraClient:
        """
        Connects to the temperature controller.

        Returns:
            The KiutraClient instance for the temperature controller.

        Raises:
            ConnectionError: If connection to the temperature controller fails.
        """
        try:
            self.controller = TemperatureControl(
                "temperature_control", self.parent._address, self.parent._port
            )
        except Exception as e:
            error_msg = (
                f"Failed to connect to temperature controller at "
                f"{self.parent._address}:{self.parent._port}. "
                f"Original error: {e}"
            )
            log.exception(error_msg)
            raise ConnectionError(error_msg) from e
        else:
            return self.controller

    def _connect_adr_controller(self) -> KiutraClient:
        """
        Connects to the ADR controller.

        Returns:
            The KiutraClient instance for the ADR controller.

        Raises:
            ConnectionError: If connection to the ADR controller fails.
        """
        try:
            self.adr_controller = ADRControl(
                "adr_control", self.parent._address, self.parent._port
            )
        except Exception as e:
            error_msg = (
                f"Failed to connect to adr controller at "
                f"{self.parent._address}:{self.parent._port}. "
                f"Original error: {e}"
            )
            log.exception(error_msg)
            raise ConnectionError(error_msg) from e
        else:
            return self.adr_controller


    def _set_temperature(self, value: float) -> None:
        """
        Sets the temperature of the channel.

        If the controller is idle, it starts a temperature ramp to the specified
        value using the current control_mode. Blocks until the temperature is stable
        or timeout occurs, depending on the 'blocking' parameter setting.

        Args:
            value: The target temperature in Kelvin.

        Raises:
            TimeoutError: If the temperature does not stabilize within the timeout period
                         and blocking mode is enabled.
        """
        ramp = self.ramp()
        self.temperature_setpoint(value)
        control_mode = self.operation_mode()
        self.controller.call_method("start_control", setpoint=value, ramp=ramp, control_mode=control_mode)

        if self.blocking():
            timeout = self.timeout()
            self._wait_for_temperature(timeout=timeout, check_interval=1.0)

    def _wait_for_temperature(self, timeout: float = 3600.0, check_interval: float = 1.0) -> None:
        """
        Waits for the temperature controller to reach a stable state.

        This method blocks until the controller status indicates "done" or "stable",
        or until the timeout is reached.

        Args:
            timeout: Maximum time to wait in seconds (default: 3600s = 1 hour).
            check_interval: Time between status checks in seconds (default: 1.0s).

        Raises:
            TimeoutError: If the temperature does not stabilize within the timeout period.
        """
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                status = self.status()
                raise TimeoutError(
                    f"Temperature did not stabilize within {timeout} seconds. "
                    f"Current status: {status}"
                )

            if self.stable():
                log.info(f"Temperature stabilized. Status: {self.status()}")
                return

            time.sleep(check_interval)


    def wait_for_stable(self, timeout: Optional[float] = None, check_interval: float = 1.0) -> None:
        """
        Manually wait for the temperature to stabilize.

        This is useful when temperature was set with blocking=False and you want to
        wait for stabilization later.

        Args:
            timeout: Maximum time to wait in seconds. If None, uses the timeout parameter value.
            check_interval: Time between status checks in seconds (default: 1.0s).

        Raises:
            TimeoutError: If the temperature does not stabilize within the timeout period.
        """
        if timeout is None:
            timeout = float(self.timeout())
        self._wait_for_temperature(timeout=timeout, check_interval=check_interval)

    def recharge_adr(self) -> None:
        """
        Recharges the ADR.

        This method calls the recharge function of the ADR controller.
        """
        if not isinstance(self.adr_controller, ADRControl):
            raise TypeError("ADR controller is not an ADRControl instance.")
        self.adr_controller.call_method("recharge")



class MagnetChannel(InstrumentChannel):
    """
    QCoDeS driver for a magnet channel of the Kiutra L-Type Rapid cryostat.

    Args:
        parent: The parent instrument (LTypeRapid).
        name: The name of the magnet channel.
    """

    controller: MagnetControl

    def __init__(
        self,
        parent: "LTypeRapid",
        name: str,
    ) -> None:
        super().__init__(parent, name)

        self._connect_magnet_controller()
        self.field_validator = Numbers(-5.5, 5.5)

        self.field: Parameter = self.add_parameter(
            "field",
            label="Magnetic Field",
            unit="T",
            get_cmd=lambda: self.controller.field,
            set_cmd=self._set_field,
            vals=self.field_validator,
        )
        """Parameter field"""

        self.field_setpoint: Parameter = self.add_parameter(
            "field_setpoint",
            label="Magnetic Field Setpoint",
            get_cmd=lambda: self.controller.setpoint,
            set_cmd=lambda value: self.controller.set_value("setpoint", value),
            unit="T",
            vals=self.field_validator,
        )
        """Parameter field_setpoint"""

        self.ramp: Parameter = self.add_parameter(
            "ramp",
            parameter_class=Parameter,
            get_cmd=lambda: self.controller.ramp,
            set_cmd=lambda value: self.controller.set_value("ramp", value),
            label="Magnetic Field Ramp Rate",
            unit="T/min",
            vals=Numbers(0, 0.5),
        )
        """Parameter field_ramp"""

        self.status: Parameter = self.add_parameter(
            "status",
            label="Magnet controller status",
            get_cmd=lambda: self.controller.query_value('status'),
            docstring="Current status of the magnet controller as (status_code, status_message).",
        )
        """Parameter status"""

        self.stable: Parameter = self.add_parameter(
            "stable",
            label="Field stability status",
            get_cmd=lambda: self.controller.query_value('status')[0] == 200,
            docstring="True if the magnet controller is in a stable state (status is 200).",
        )
        """Parameter stable"""

        self.blocking: ManualParameter = self.add_parameter(
            "blocking",
            parameter_class=ManualParameter,
            label="Blocking mode for field setting",
            initial_value=True,
            vals=Enum(True, False),
            docstring="If True, field setter waits for stabilization. If False, returns immediately.",
        )
        """Parameter blocking"""

        self.timeout: ManualParameter = self.add_parameter(
            "timeout",
            parameter_class=ManualParameter,
            label="Timeout for field stabilization",
            unit="s",
            initial_value=3600.0,
            vals=Numbers(0, float('inf')),
            docstring="Maximum time to wait for field stabilization in seconds.",
        )
        """Parameter timeout"""

    def _set_field(self, field: float) -> None:
        """
        Starts a magnetic field ramp.

        This method allows setting the field setpoint and ramp rate before
        starting the ramp. If `field` or `ramp` are not provided, the previously
        set values will be used.

        Args:
            field: The target magnetic field in Tesla.
            ramp: The ramp rate in Tesla per minute.
        """
        self.field_setpoint(field)
        self.controller.start(setpoint=self.field_setpoint(), ramp=self.ramp())
        if self.blocking():
            timeout = self.timeout()
            self._wait_for_field(timeout=timeout, check_interval=1.0)


    def _connect_magnet_controller(self) -> KiutraClient:
        """
        Connects to the magnet controller.

        Returns:
            The KiutraClient instance for the magnet controller.

        Raises:
            ConnectionError: If connection to the magnet controller fails.
        """
        try:
            self.controller = MagnetControl(
                "sample_magnet", self.parent._address, self.parent._port
            )
        except Exception as e:
            error_msg = (
                f"Failed to connect to magnet controller at "
                f"{self.parent._address}:{self.parent._port}. "
                f"Original error: {e}"
            )
            log.exception(error_msg)
            raise ConnectionError(error_msg) from e
        else:
            return self.controller

    def _wait_for_field(self, timeout: float = 3600.0, check_interval: float = 1.0) -> None:
        """
        Waits for the field controller to reach a stable state.

        This method blocks until the controller status indicates "done" or "stable",
        or until the timeout is reached.

        Args:
            timeout: Maximum time to wait in seconds (default: 3600s = 1 hour).
            check_interval: Time between status checks in seconds (default: 1.0s).

        Raises:
            TimeoutError: If the field does not stabilize within the timeout period.
        """
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                status = self.status()
                raise TimeoutError(
                    f"Field did not stabilize within {timeout} seconds. "
                    f"Current status: {status}"
                )

            if self.stable():
                log.info(f"Field stabilized. Status: {self.status()}")
                return

            time.sleep(check_interval)


    def wait_for_stable(self, timeout: Optional[float] = None, check_interval: float = 1.0) -> None:
        """
        Manually wait for the field to stabilize.

        This is useful when field was set with blocking=False and you want to
        wait for stabilization later.

        Args:
            timeout: Maximum time to wait in seconds. If None, uses the timeout parameter value.
            check_interval: Time between status checks in seconds (default: 1.0s).

        Raises:
            TimeoutError: If the field does not stabilize within the timeout period.
        """
        if timeout is None:
            timeout = float(self.timeout())
        self._wait_for_field(timeout=timeout, check_interval=check_interval)


class LTypeRapid(Instrument):
    """
    QCoDeS driver for the Kiutra L-Type Rapid cryostat.

    Args:
        name: Instrument name.
        address: IP address of the Kiutra controller.
        port: Port number for the Kiutra controller (default is 1006).
        kwargs: Additional keyword arguments passed to the Instrument base class.
    """

    def __init__(
        self,
        name: str,
        address: str,
        port: int = 1006,
        **kwargs: "Unpack[InstrumentBaseKWArgs]",
    ) -> None:
        super().__init__(name, **kwargs)

        self._address = address
        self._port = port
        temperature_control = TemperatureChannel(self, "temperature_control")
        magnet_control = MagnetChannel(self, "magnet_control")
        self.add_submodule("temperature_control", temperature_control)
        self.add_submodule("magnet_control", magnet_control)

    def get_idn(self):
        return {'vendor': 'Kiutra',
                'model': 'L-Type Rapid',
                'serial': '',
                'firmware': ''}
