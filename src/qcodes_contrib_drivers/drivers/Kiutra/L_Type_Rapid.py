from kiutra_api.controller_interfaces import (
    TemperatureControl,
    MagnetControl,
    ADRControl,
    HeaterControl,
)
from kiutra_api.api_client import KiutraClient


from typing import TYPE_CHECKING, Optional

import numpy as np
from qcodes.instrument import Instrument, InstrumentBaseKWArgs, InstrumentChannel
from qcodes.parameters import (
    ManualParameter,
    MultiParameter,
    Parameter,
    ParamRawDataType,
    GroupParameter,
    Group,
)
from qcodes.validators import Enum, Numbers, Validator

if TYPE_CHECKING:
    from typing_extensions import Unpack

numbertypes = float | int | np.floating | np.integer


class ADRRampValidator(Validator[numbertypes]):
    """
    Requires a number of type int, float, numpy.integer or numpy.floating.
    Depends on the ramp limits set in the ADR controller.

    Raises:
        TypeError: If instrument.controller used with this validator is not ADRControl.

    """

    is_numeric = True

    def __init__(self) -> None:
        if not isinstance(self.instrument.controller, ADRControl):
            raise TypeError("ADRRampValidator can only be used with ADRControl.")
        # Get the ramp limits from the instrument: [[temp_min, temp_max, ramp_max], ...]
        self._valid_values = self.instrument.controller.query("ramp_limits")

    def validate(self, value: numbertypes, context: str = "") -> None:
        """_summary_

        Args:
            value (numbertypes): A rate value.
            context (str, optional): Context for validation.

        Raises:
            TypeError: If not int or float.
            ValueError: If number is not between the min and the max value.
        """

        if not isinstance(value, (int, float, np.integer, np.floating)):
            raise TypeError(f"{value!r} is not an int or float; {context}")
        setpoint = self.instrument.temperature_setpoint

        for temp_min, temp_max, ramp_max in self._valid_values:
            if temp_min <= setpoint < temp_max:
                if not (0 <= value <= ramp_max):
                    raise ValueError(
                        f"Ramp rate {value} K/min is out of bounds for setpoint {setpoint} K. "
                        f"Valid range is 0 to {ramp_max} K/min."
                    )


class TemperatureChannel(InstrumentChannel):
    """
    QCoDeS driver for a temperature channel of the Kiutra L-Type Rapid cryostat.

    Args:
        parent: The parent instrument (LTypeRapid).
        name: The name of the temperature channel.
        channel_id: The identifier for the temperature channel.
    """

    def __init__(
        self,
        parent: "LTypeRapid",
        name: str,
    ) -> None:
        super().__init__(parent, name)

        self.controller = self._connect_temperature_controller()

        self.add_parameter(
            "temperature",
            label="Temperature",
            unit="K",
            get_cmd=self.controller.kelvin,
            set_cmd=self._set_temperature,
            vals=Numbers(0.083, 300.0),
        )

        self.add_parameter(
            "ramp",
            label="Temperature ramp rate",
            unit="K/min",
            get_cmd=self.controller.ramp,
            set_cmd=self.controller.ramp,
        )

        self.add_parameter(
            "temperature_setpoint",
            label="Temperature setpoint",
            unit="K",
            get_cmd=self.controller.setpoint,
            set_cmd=self.controller.setpoint,
        )

    def _connect_temperature_controller(self) -> KiutraClient:
        self.controller = TemperatureControl(
            "temperature_control", self.parent._address, self.parent._port
        )
        return self.controller

    def _set_temperature(self, value: float) -> None:
        ramp = self.ramp
        self.temperature_setpoint = value
        if self.controller.state == "IDLE":
            self.controller.start(setpoint=value, ramp=ramp)


class ADRChannel(InstrumentChannel):
    """
    QCoDeS driver for an ADR channel of the Kiutra L-Type Rapid cryostat.

    Args:
        parent: The parent instrument (LTypeRapid).
        name: The name of the ADR channel.
    """

    def __init__(
        self,
        parent: "LTypeRapid",
        name: str,
    ) -> None:
        super().__init__(parent, name)

        self.controller = self._connect_adr_controller()

        self.add_parameter(
            "temperature",
            label="ADR Temperature",
            unit="K",
            get_cmd=self.controller.kelvin,
            set_cmd=self._set_temperature,
            vals=Numbers(0.083, 8.0),
        )

        self.add_parameter(
            "ramp",
            label="ADR Ramp Rate",
            unit="K/min",
            get_cmd=self.controller.ramp,
            set_cmd=self.controller.ramp,
            vals=ADRRampValidator,
        )

        self.add_parameter(
            "temperature_setpoint",
            label="ADR Temperature Setpoint",
            unit="K",
            get_cmd=self.controller.setpoint,
            set_cmd=self.controller.setpoint,
        )

        self.add_parameter(
            "operation_mode",
            label="ADR Operation Mode",
            get_cmd=self.controller.operation_mode,
            set_cmd=self.controller.operation_mode,
            vals=Enum("cadr", "adr"),
            docstring="Sets the operation mode of the ADR. Options are 'cadr' (continuous ADR) and 'adr' (single-shot ADR).",
        )

    def _connect_adr_controller(self) -> KiutraClient:
        self.controller = ADRControl(
            "adr_control", self.parent._address, self.parent._port
        )
        return self.controller

    def _set_temperature(self, value: float) -> None:
        ramp = self.ramp
        self.temperature_setpoint = value
        try:
            self.ramp.validate(ramp)
        except ValueError as e:
            valid_values_text = f"Valid ramp rates are ([[min_temp, temp_max, max_rate], ...]): {self.ramp.get_valid_values()} K/min"
            self.log.error(f"Failed to set ADR temperature: {e}")
            raise ValueError(
                f"Cannot set temperature to {value} K with ramp rate {ramp} K/min. {valid_values_text}"
            )

        if self.controller.state == "IDLE":
            self.controller.start(setpoint=value, ramp=ramp)


class HeaterChannel(InstrumentChannel):
    """
    QCoDeS driver for a heater channel of the Kiutra L-Type Rapid cryostat.

    Args:
        parent: The parent instrument (LTypeRapid).
        name: The name of the heater channel.
    """

    def __init__(
        self,
        parent: "LTypeRapid",
        name: str,
    ) -> None:
        super().__init__(parent, name)

        self.controller = self._connect_heater_controller()

        self.add_parameter(
            "power",
            label="Heater Power",
            unit="W",
            get_cmd=self.controller.power,
        )
        self.add_parameter(
            "temperature_setpoint",
            label="Heater Temperature Setpoint",
            unit="K",
            get_cmd=self.controller.setpoint,
            set_cmd=self.controller.setpoint,
        )

        self.add_parameter(
            "temperature",
            label="Heater Temperature",
            unit="K",
            get_cmd=self.controller.kelvin,
            set_cmd=self._set_temperature,
            vals=Numbers(3.0, 300.0),
        )

        self.add_parameter(
            "ramp",
            label="Heater Ramp Rate",
            unit="K/min",
            get_cmd=self.controller.ramp,
            set_cmd=self.controller.ramp,
        )

    def _connect_heater_controller(self) -> KiutraClient:
        self.controller = HeaterControl(
            "sample_heater", self.parent._address, self.parent._port
        )
        return self.controller

    def _set_temperature(self, value: float) -> None:
        self.temperature_setpoint = value
        self.controller.start(setpoint=value, ramp=self.ramp)


class MagnetChannel(InstrumentChannel):
    """
    QCoDeS driver for a magnet channel of the Kiutra L-Type Rapid cryostat.

    Args:
        parent: The parent instrument (LTypeRapid).
        name: The name of the magnet channel.
    """

    def __init__(
        self,
        parent: "LTypeRapid",
        name: str,
    ) -> None:
        super().__init__(parent, name)

        self.controller = self._connect_magnet_controller()

        self.add_parameter(
            "field",
            label="Magnetic Field",
            unit="T",
            get_cmd=self.controller.field,
            set_cmd=False,
        )

        self.add_parameter(
            "field_setpoint",
            initial_value=0.0,
            label="Magnetic Field Setpoint",
            unit="T",
            parameter_class=ManualParameter,
            vals=Numbers(-5, 5),  # Please adjust the validator values as needed
        )

        self.add_parameter(
            "field_rate",
            initial_value=0.0,
            label="Magnetic Field Ramp Rate",
            unit="T/min",
            parameter_class=ManualParameter,
            vals=Numbers(0, 0.5),  # Please adjust the validator values as needed
        )

    def start_ramp(
        self, field: Optional[float] = None, ramp: Optional[float] = None
    ) -> None:
        if field is not None:
            self.field_setpoint = field
        if ramp is not None:
            self.field_rate = ramp
        self.controller.start(setpoint=self.field_setpoint, ramp=self.field_rate)

    def _connect_magnet_controller(self) -> KiutraClient:
        self.controller = MagnetControl(
            "sample_magnet", self.parent._address, self.parent._port
        )
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
        adr_control = ADRChannel(self, "adr_control")
        heater_control = HeaterChannel(self, "heater_control")
        magnet_control = MagnetChannel(self, "magnet_control")
        self.add_submodule("temperature_control", temperature_control)
        self.add_submodule("adr_control", adr_control)
        self.add_submodule("heater_control", heater_control)
        self.add_submodule("magnet_control", magnet_control)
