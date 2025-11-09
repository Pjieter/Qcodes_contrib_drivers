from typing import TYPE_CHECKING, Optional
from collections.abc import Callable
import logging

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
        temperature_setpoint: The current temperature setpoint.

    """

    is_numeric = True

    def __init__(
        self,
        ramp_limits: list[tuple[numbertypes, numbertypes, numbertypes]],
        temperature_setpoint_getter: Callable[[], float],
    ) -> None:
        """Initializes the ADRRampValidator."""
        self._ramp_limits = ramp_limits
        self._temperature_setpoint_getter = temperature_setpoint_getter
        # Initialize to avoid attribute error, set to proper values in validate.
        self._valid_values = (0, 0)

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
        setpoint = self._temperature_setpoint_getter()
        last_temp_max = self._ramp_limits[-1][1]
        for temp_min, temp_max, ramp_max in self._ramp_limits:
            # Make upper bound inclusive for the final interval
            is_in_range = (temp_min <= setpoint < temp_max) or (
                setpoint == temp_max == last_temp_max
            )
            if is_in_range:
                self._valid_values = (0, ramp_max)
                if not (0 <= value <= ramp_max):
                    raise ValueError(
                        f"Ramp rate {value} K/min is out of bounds for setpoint {setpoint} K. "
                        f"Valid range is 0 to {ramp_max} K/min.; {context}"
                    )
                return
        raise ValueError(f"No valid ramp rate found for setpoint {setpoint} K.")


class TemperatureChannel(InstrumentChannel):
    """
    QCoDeS driver for a temperature channel of the Kiutra L-Type Rapid cryostat.

    Args:
        parent: The parent instrument (LTypeRapid).
        name: The name of the temperature channel.
    """

    controller: TemperatureControl

    def __init__(
        self,
        parent: "LTypeRapid",
        name: str,
    ) -> None:
        super().__init__(parent, name)

        self._connect_temperature_controller()
        self.temperature_validator = Numbers(0.083, 300.0)

        self.temperature: Parameter = self.add_parameter(
            "temperature",
            label="Temperature",
            unit="K",
            get_cmd=self.controller.kelvin,
            set_cmd=self._set_temperature,
            vals=self.temperature_validator,
        )
        """Parameter temperature"""

        self.ramp: Parameter = self.add_parameter(
            "ramp",
            label="Temperature ramp rate",
            unit="K/min",
            get_cmd=self.controller.ramp,
            set_cmd=self.controller.ramp,
            vals=Numbers(0, 5.0),
        )
        """Parameter ramp"""

        self.temperature_setpoint: Parameter = self.add_parameter(
            "temperature_setpoint",
            label="Temperature setpoint",
            unit="K",
            get_cmd=self.controller.setpoint,
            set_cmd=self.controller.setpoint,
            vals=self.temperature_validator,
        )
        """Parameter temperature_setpoint"""

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
            return self.controller
        except Exception as e:
            self.controller = None
            error_msg = (
                f"Failed to connect to temperature controller at "
                f"{self.parent._address}:{self.parent._port}. "
                f"Original error: {e}"
            )
            log.error(error_msg)
            raise ConnectionError(error_msg) from e

    def _set_temperature(self, value: float) -> None:
        """
        Sets the temperature of the channel.

        If the controller is idle, it starts a temperature ramp to the specified
        value.

        Args:
            value: The target temperature in Kelvin.
        """
        ramp = self.ramp()
        self.temperature_setpoint(value)
        if self.controller.state == "IDLE":
            self.controller.start(setpoint=value, ramp=ramp)


class ADRChannel(InstrumentChannel):
    """
    QCoDeS driver for an ADR channel of the Kiutra L-Type Rapid cryostat.

    Args:
        parent: The parent instrument (LTypeRapid).
        name: The name of the ADR channel.
    """

    controller: ADRControl

    def __init__(
        self,
        parent: "LTypeRapid",
        name: str,
    ) -> None:
        super().__init__(parent, name)

        self._connect_adr_controller()
        self.temperature_validator = Numbers(0.083, 8.0)

        self.temperature: Parameter = self.add_parameter(
            "temperature",
            label="ADR Temperature",
            unit="K",
            get_cmd=self.controller.kelvin,
            set_cmd=self._set_temperature,
            vals=self.temperature_validator,
        )
        """Parameter temperature"""

        self.temperature_setpoint: Parameter = self.add_parameter(
            "temperature_setpoint",
            label="ADR Temperature Setpoint",
            unit="K",
            get_cmd=self.controller.setpoint,
            set_cmd=self.controller.setpoint,
            vals=self.temperature_validator,
        )
        """Parameter temperature_setpoint"""

        self.ramp: Parameter = self.add_parameter(
            "ramp",
            label="ADR Ramp Rate",
            unit="K/min",
            get_cmd=self.controller.ramp,
            set_cmd=self.controller.ramp,
            vals=ADRRampValidator(
                ramp_limits=self.controller.query_value("ramp_limits"),
                temperature_setpoint_getter=self.temperature_setpoint,
            ),
        )
        """Parameter ramp"""

        self.operation_mode: Parameter = self.add_parameter(
            "operation_mode",
            label="ADR Operation Mode",
            initial_value="cadr",
            get_cmd=self.controller.operation_mode,
            set_cmd=self.controller.operation_mode,
            vals=Enum("cadr", "adr"),
            docstring="Sets the operation mode of the ADR. Options are 'cadr' (continuous ADR) and 'adr' (single-shot ADR).",
        )
        """Parameter operation_mode"""

    def _connect_adr_controller(self) -> KiutraClient:
        """
        Connects to the ADR controller.

        Returns:
            The KiutraClient instance for the ADR controller.

        Raises:
            ConnectionError: If connection to the ADR controller fails.
        """
        try:
            self.controller = ADRControl(
                "adr_control", self.parent._address, self.parent._port
            )
            return self.controller
        except Exception as e:
            self.controller = None
            error_msg = (
                f"Failed to connect to ADR controller at "
                f"{self.parent._address}:{self.parent._port}. "
                f"Original error: {e}"
            )
            log.error(error_msg)
            raise ConnectionError(error_msg) from e

    def _set_temperature(self, value: float) -> None:
        """
        Sets the temperature of the ADR.

        This method sets the temperature setpoint and then re-validates the ramp
        rate. If the controller is idle, it starts the ADR temperature ramp.

        Args:
            value: The target temperature in Kelvin.
        """
        ramp = self.ramp()
        self.temperature_setpoint(value)
        self.ramp(
            ramp
        )  # Force re-setting ramp to ensure validator check after new setpoint

        if self.controller.state == "IDLE":
            self.controller.start(setpoint=value, ramp=ramp)


class HeaterChannel(InstrumentChannel):
    """
    QCoDeS driver for a heater channel of the Kiutra L-Type Rapid cryostat.

    Args:
        parent: The parent instrument (LTypeRapid).
        name: The name of the heater channel.
    """

    controller: HeaterControl

    def __init__(
        self,
        parent: "LTypeRapid",
        name: str,
    ) -> None:
        super().__init__(parent, name)

        self._connect_heater_controller()
        self.temperature_validator = Numbers(0.083, 300.0)

        self.power: Parameter = self.add_parameter(
            "power",
            label="Heater Power",
            unit="W",
            get_cmd=self.controller.power,
        )
        """Parameter power"""

        self.temperature_setpoint: Parameter = self.add_parameter(
            "temperature_setpoint",
            label="Heater Temperature Setpoint",
            unit="K",
            get_cmd=self.controller.setpoint,
            set_cmd=self.controller.setpoint,
            vals=self.temperature_validator,
        )
        """Parameter temperature_setpoint"""

        self.temperature: Parameter = self.add_parameter(
            "temperature",
            label="Heater Temperature",
            unit="K",
            get_cmd=self.controller.kelvin,
            set_cmd=self._set_temperature,
            vals=self.temperature_validator,
        )
        """Parameter temperature"""

        self.ramp: Parameter = self.add_parameter(
            "ramp",
            label="Heater Ramp Rate",
            unit="K/min",
            get_cmd=self.controller.ramp,
            set_cmd=self.controller.ramp,
        )
        """Parameter ramp"""

    def _connect_heater_controller(self) -> KiutraClient:
        """
        Connects to the heater controller.

        Returns:
            The KiutraClient instance for the heater controller.

        Raises:
            ConnectionError: If connection to the heater controller fails.
        """
        try:
            self.controller = HeaterControl(
                "sample_heater", self.parent._address, self.parent._port
            )
            return self.controller
        except Exception as e:
            self.controller = None
            error_msg = (
                f"Failed to connect to heater controller at "
                f"{self.parent._address}:{self.parent._port}. "
                f"Original error: {e}"
            )
            log.error(error_msg)
            raise ConnectionError(error_msg) from e

    def _set_temperature(self, value: float) -> None:
        """
        Sets the temperature of the heater.

        Args:
            value: The target temperature in Kelvin.
        """
        self.temperature_setpoint(value)
        if self.controller.state == "IDLE":
            self.controller.start(setpoint=value, ramp=self.ramp())


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
        self.field_validator = Numbers(-5, 5)

        self.field: Parameter = self.add_parameter(
            "field",
            label="Magnetic Field",
            unit="T",
            get_cmd=self.controller.field,
            set_cmd=False,
            vals=self.field_validator,
        )
        """Parameter field"""

        self.field_setpoint: ManualParameter = self.add_parameter(
            "field_setpoint",
            parameter_class=ManualParameter,
            initial_value=0.0,
            label="Magnetic Field Setpoint",
            unit="T",
            vals=self.field_validator,
        )
        """Parameter field_setpoint"""

        self.field_rate: ManualParameter = self.add_parameter(
            "field_rate",
            parameter_class=ManualParameter,
            initial_value=0.0,
            label="Magnetic Field Ramp Rate",
            unit="T/min",
            vals=Numbers(0, 0.5),
        )
        """Parameter field_rate"""

    def start_ramp(
        self, field: Optional[float] = None, ramp: Optional[float] = None
    ) -> None:
        """
        Starts a magnetic field ramp.

        This method allows setting the field setpoint and ramp rate before
        starting the ramp. If `field` or `ramp` are not provided, the previously
        set values will be used.

        Args:
            field: The target magnetic field in Tesla.
            ramp: The ramp rate in Tesla per minute.
        """
        if field is not None:
            self.field_setpoint(field)
        if ramp is not None:
            self.field_rate(ramp)
        self.controller.start(setpoint=self.field_setpoint(), ramp=self.field_rate())

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
            return self.controller
        except Exception as e:
            self.controller = None
            error_msg = (
                f"Failed to connect to magnet controller at "
                f"{self.parent._address}:{self.parent._port}. "
                f"Original error: {e}"
            )
            log.error(error_msg)
            raise ConnectionError(error_msg) from e


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
        adr_control = ADRChannel(self, "adr_control")
        heater_control = HeaterChannel(self, "heater_control")
        magnet_control = MagnetChannel(self, "magnet_control")
        self.add_submodule("temperature_control", temperature_control)
        self.add_submodule("adr_control", adr_control)
        self.add_submodule("heater_control", heater_control)
        self.add_submodule("magnet_control", magnet_control)
