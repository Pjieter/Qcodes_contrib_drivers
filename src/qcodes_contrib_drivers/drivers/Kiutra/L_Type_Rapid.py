from typing import TYPE_CHECKING, Optional
from collections.abc import Callable
import logging
import time

import numpy as np
from qcodes.instrument import Instrument, InstrumentBaseKWArgs, InstrumentChannel
from qcodes.parameters import ManualParameter, Parameter
from qcodes.validators import Bool, Enum, Numbers, Validator
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


def _wait_until_started(
    stable: Callable[[], bool],
    settle_timeout: float,
    check_interval: float,
) -> bool:
    """
    Waits for a controller to acknowledge a newly started sequence.

    Immediately after a ramp is started the controller can still report the
    stable status (200) left over from the previous setpoint, so polling for
    stability straight away would return at the old value. This helper waits
    until the controller reports a non-stable status (210 initializing or 220
    ramping), which marks the new sequence as actually running.

    Args:
        stable: Callable returning True while the controller reports status 200.
        settle_timeout: Maximum time to wait in seconds.
        check_interval: Time between status checks in seconds.

    Returns:
        True if the controller left the stable status within ``settle_timeout``,
        False if it kept reporting a stable status (the setpoint was most likely
        already reached).
    """
    start_time = time.time()
    while time.time() - start_time < settle_timeout:
        if not stable():
            return True
        time.sleep(check_interval)
    return False


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


class _StabilizingChannel(InstrumentChannel):
    """
    Base for channels that start a ramp and then wait for it to settle.

    The temperature and magnet channels drive different controllers, but the
    settling machinery around them is the same: the same four parameters, the
    same polling loop, and the same guard against acting on a stable status
    left over from the previous setpoint.

    A subclass sets :attr:`_quantity` and :attr:`_controller_name`, assigns
    ``self.controller``, and then calls :meth:`_add_stability_parameters`.
    """

    #: What this channel ramps, as it appears in labels and messages.
    _quantity: str = ""

    #: How this channel's controller is named in parameter documentation.
    _controller_name: str = ""

    @property
    def _quantity_title(self) -> str:
        """The ramped quantity with a leading capital, for messages."""
        return self._quantity[:1].upper() + self._quantity[1:]

    def _add_stability_parameters(self) -> None:
        """
        Adds the status, stable, blocking and timeout parameters.

        Called by subclasses once ``self.controller`` is connected.
        """
        quantity = self._quantity
        controller = self._controller_name
        controller_title = controller[:1].upper() + controller[1:]

        self.status: Parameter = self.add_parameter(
            "status",
            label=f"{controller_title} status",
            get_cmd=lambda: self.controller.query_value("status"),
            docstring=(
                f"Current status of the {controller} as "
                f"(status_code, status_message)."
            ),
        )
        """Parameter status"""

        self.stable: Parameter = self.add_parameter(
            "stable",
            label=f"{self._quantity_title} stability status",
            get_cmd=lambda: self.controller.query_value("status")[0] == 200,
            docstring=(
                f"True if the {controller} is in a stable state (status is 200)."
            ),
        )
        """Parameter stable"""

        self.blocking: ManualParameter = self.add_parameter(
            "blocking",
            parameter_class=ManualParameter,
            label=f"Blocking mode for {quantity} setting",
            initial_value=True,
            vals=Bool(),
            docstring=(
                f"If True, {quantity} setter waits for stabilization. "
                f"If False, returns immediately."
            ),
        )
        """Parameter blocking"""

        self.timeout: ManualParameter = self.add_parameter(
            "timeout",
            parameter_class=ManualParameter,
            label=f"Timeout for {quantity} stabilization",
            unit="s",
            initial_value=3600.0,
            vals=Numbers(0, float("inf")),
            docstring=(
                f"Maximum time to wait for {quantity} stabilization in seconds."
            ),
        )
        """Parameter timeout"""

    def _wait_for_stable_status(
        self,
        timeout: float = 3600.0,
        check_interval: float = 1.0,
        settle_timeout: float = 10.0,
    ) -> None:
        """
        Waits for the controller to reach a stable state.

        Immediately after a ramp is started the controller can still report the
        stable status (200) left over from the previous setpoint, so this first
        waits for it to report a non-stable status. If that does not happen
        within ``settle_timeout`` the setpoint is assumed to have been reached
        already and stabilization is not awaited.

        Args:
            timeout: Maximum time to wait in seconds (default: 3600s = 1 hour).
            check_interval: Time between status checks in seconds (default: 1.0s).
            settle_timeout: Maximum time to wait for the controller to leave the
                stable status (200) before assuming the setpoint was already
                reached (default: 10.0s).

        Raises:
            TimeoutError: If the controller does not stabilize within the
                timeout period.
        """
        quantity = self._quantity_title

        if not _wait_until_started(self.stable, settle_timeout, check_interval):
            log.info(
                f"{quantity} controller still reports a stable status after "
                f"{settle_timeout} s; assuming the setpoint was already reached. "
                f"Status: {self.status()}"
            )
            return

        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                status = self.status()
                raise TimeoutError(
                    f"{quantity} did not stabilize within {timeout} seconds. "
                    f"Current status: {status}"
                )

            if self.stable():
                log.info(f"{quantity} stabilized. Status: {self.status()}")
                return

            time.sleep(check_interval)

    def wait_for_stable(
        self,
        timeout: Optional[float] = None,
        check_interval: float = 1.0,
        settle_timeout: float = 10.0,
    ) -> None:
        """
        Manually wait for the channel to stabilize.

        This is useful when the setpoint was applied with blocking=False and you
        want to wait for stabilization later.

        Args:
            timeout: Maximum time to wait in seconds. If None, uses the timeout
                parameter value.
            check_interval: Time between status checks in seconds (default: 1.0s).
            settle_timeout: Maximum time to wait for the controller to leave the
                stable status (200) before assuming the setpoint was already
                reached (default: 10.0s).

        Raises:
            TimeoutError: If the channel does not stabilize within the timeout
                period.
        """
        if timeout is None:
            timeout = float(self.timeout())
        self._wait_for_stable_status(
            timeout=timeout,
            check_interval=check_interval,
            settle_timeout=settle_timeout,
        )


class TemperatureChannel(_StabilizingChannel):
    """
    QCoDeS driver for a temperature channel of the Kiutra L-Type Rapid cryostat.

    Setting ``temperature`` starts a ramp. By default the setter blocks until the
    controller reports a stable status, so that a measurement taken straight
    after the set is really taken at the requested temperature. This follows the
    convention of the QCoDeS AMI430 magnet driver, whose ``block_during_ramp``
    parameter also defaults to True.

    Two parameters control this:

    * ``blocking`` (default True) -- whether the temperature setter waits at all.
      Set it to False for fire-and-forget ramps, then call
      :meth:`wait_for_stable` when you want to wait.
    * ``timeout`` (default 3600 s) -- how long the setter waits before giving up.

    .. warning::
       With ``blocking`` set to True a temperature that never stabilizes raises
       ``TimeoutError`` from inside the setter. In a sweep this aborts the whole
       measurement, so pick a ``timeout`` that suits the slowest step of the
       sweep, or set ``blocking`` to False and wait explicitly.

    Args:
        parent: The parent instrument (LTypeRapid).
        name: The name of the temperature channel.
    """

    _quantity = "temperature"
    _controller_name = "temperature controller"

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

        self._add_stability_parameters()




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
            self._wait_for_stable_status(timeout=timeout, check_interval=1.0)




    def recharge_adr(self) -> None:
        """
        Recharges the ADR.

        This method calls the recharge function of the ADR controller.
        """
        if not isinstance(self.adr_controller, ADRControl):
            raise TypeError("ADR controller is not an ADRControl instance.")
        self.adr_controller.call_method("recharge")



class MagnetChannel(_StabilizingChannel):
    """
    QCoDeS driver for a magnet channel of the Kiutra L-Type Rapid cryostat.

    Setting ``field`` starts a ramp. By default the setter blocks until the
    controller reports a stable status, so that a measurement taken straight
    after the set is really taken at the requested field. This follows the
    convention of the QCoDeS AMI430 magnet driver, whose ``block_during_ramp``
    parameter also defaults to True.

    Two parameters control this:

    * ``blocking`` (default True) -- whether the field setter waits at all.
      Set it to False for fire-and-forget ramps, then call
      :meth:`wait_for_stable` when you want to wait.
    * ``timeout`` (default 3600 s) -- how long the setter waits before giving up.

    .. warning::
       With ``blocking`` set to True a field that never stabilizes raises
       ``TimeoutError`` from inside the setter. In a sweep this aborts the whole
       measurement, so pick a ``timeout`` that suits the slowest step of the
       sweep, or set ``blocking`` to False and wait explicitly.

    Args:
        parent: The parent instrument (LTypeRapid).
        name: The name of the magnet channel.
    """

    _quantity = "field"
    _controller_name = "magnet controller"

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

        self._add_stability_parameters()




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
            self._wait_for_stable_status(timeout=timeout, check_interval=1.0)


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
