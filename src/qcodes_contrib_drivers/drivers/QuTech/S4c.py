from typing import TYPE_CHECKING, Optional

from qcodes.instrument import Instrument, InstrumentBaseKWArgs
from qcodes.parameters import (
    ManualParameter,
    Parameter,
    ParamRawDataType,
    MultiParameter,
)
from qcodes.validators import Enum

if TYPE_CHECKING:
    from typing_extensions import Unpack


class SourceParameter(Parameter):
    """
    Voltage or current source via an S4c source module.
    To be used when you want to set a voltage or current via the S4c, send the S4c's
    `source` command with the desired value to a voltage source device.
    """

    def __init__(
        self,
        source_param: Parameter,
        source_instrument: "S4c",
        name: Optional[str] = None,
    ) -> None:
        if not isinstance(source_instrument, S4c):
            raise TypeError(
                f"Expected instrument to be S4c, got {type(source_instrument).__name__}"
            )
        if source_instrument.source_mode() == "V":
            S4c_unit = "V"
            label = "Voltage Source"
        elif source_instrument.source_mode() == "I":
            S4c_unit = "A"
            label = "Current Source"
        else:
            S4c_unit = "V"
            label = "Voltage+Resistance Source"

        super().__init__(
            name=name,
            instrument=source_instrument,
            snapshot_value=True,
            label=label,
            unit=S4c_unit,
        )

        self._source_param: Parameter = source_param
        self._has_control_of.add(source_param)
        source_param.is_controlled_by.add(self)

    def get_raw(self) -> tuple[ParamRawDataType, ...]:
        """
        Get the raw and scaled source values.

        Returns:
            Tuple of (raw_source_value, scaled_source_value)
        """
        raw_source = self._source_param.get()
        total_output = self.instrument._get_total_output()
        if total_output is None:
            raise ValueError(
                f"Cannot get value: S4c total output is invalid (range: {self.instrument.range.get()})"
            )
        source_value = raw_source * total_output

        return (raw_source, source_value)

    def set_raw(self, value: ParamRawDataType) -> None:
        total_output = self.instrument._get_total_output()
        if total_output is None:
            raise ValueError(
                f"Cannot set value: S4c total output is invalid (range: {self.instrument.range.get()})"
            )
        raw_value = value / total_output
        self._source_param(raw_value)


class S4c(Instrument):
    """
    QCoDeS driver for the QuTech S4c Current/Voltage source module for IVVI rack.

    This is a virtual driver only and will not talk to your instrument.

    The S4c is a versatile voltage and current source designed for use in the IVVI rack system.

    Note that, as this is a purely virtual driver, it is the responsibility of
    the user to ensure that values set here are in accordance with the values
    set on the physical instrument.

    Documentation: https://qtwork.tudelft.nl/~schouten/ivvi/doc-mod/docs4c.htm

    Args:
        name: Name of the instrument instance.
        **kwargs: Forwarded to base class.
    """

    def __init__(
        self,
        name: str,
        **kwargs: "Unpack[InstrumentBaseKWArgs]",
    ) -> None:
        super().__init__(name, **kwargs)

        self.slot: ManualParameter = self.add_parameter(
            "slot",
            parameter_class=ManualParameter,
            initial_value="Sa",
            label="Module slot",
            vals=Enum("Sa", "Sb", "Sc", "Sd"),
            docstring="Physical slot of the S4c module. It depends on the summing module configuration to which slot Iso-in 1 (top) and Iso-in 2 (bottom) are connected.",
        )
        """Parameter slot"""

        self.source_mode: ManualParameter = self.add_parameter(
            "source_mode",
            parameter_class=ManualParameter,
            label="Source Mode",
            unit="",
            initial_value="V",
            vals=Enum("V", "I", "V+R"),
            docstring="Sets the source mode of the S4c module.",
        )

        self.range: ManualParameter = self.add_parameter(
            "range",
            parameter_class=ManualParameter,
            label="Range",
            unit="",
            initial_value="20m",
            vals=Enum("1n", "10n", "100n", "1u", "10u", "100u", "1m", "10m", "20m"),
            docstring="Sets the range of the S4c module.",
        )

        self.R_out: ManualParameter = self.add_parameter(
            "R_out",
            parameter_class=ManualParameter,
            label="Output Resistance",
            unit="",
            initial_value="R/10",
            vals=Enum("R/1000", "R/100", "R/10", "10R", "100R", "1000R"),
            docstring="Sets the output resistance for V+R mode.",
        )

        self.output_mode: ManualParameter = self.add_parameter(
            "output_mode",
            parameter_class=ManualParameter,
            label="Output Mode",
            unit="",
            initial_value="symm",
            vals=Enum("symm", "single"),
            docstring="Sets the output mode of the S4c module.",
        )

        self.x001_jumper: ManualParameter = self.add_parameter(
            "x001_jumper",
            parameter_class=ManualParameter,
            label="x0.01 jumper",
            unit="",
            initial_value=False,
            vals=Enum(False, True),
            docstring="Sets if the x0.01 jumper is installed (True) or not installed (False)",  # TODO implement automatically changing actual output depending on this setting
        )

    def _get_total_output(self) -> float:
        """
        Calculate total output value considering the source mode and range.

        Returns:
            Total output value.
        """
        # This is a placeholder implementation. Actual implementation would depend
        # on how the source mode and range affect the output.
        range_map = {
            "1n": 1e-9,
            "10n": 10e-9,
            "100n": 100e-9,
            "1u": 1e-6,
            "10u": 10e-6,
            "100u": 100e-6,
            "1m": 1e-3,
            "10m": 10e-3,
            "20m": 20e-3,
        }
        return range_map.get(self.range.get())
