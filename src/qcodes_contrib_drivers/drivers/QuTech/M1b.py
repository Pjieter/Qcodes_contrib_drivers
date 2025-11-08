from typing import TYPE_CHECKING

from qcodes.instrument import Instrument, InstrumentBaseKWArgs
from qcodes.parameters import (
    ManualParameter,
    MultiParameter,
    Parameter,
    ParamRawDataType,
)
from qcodes.validators import Bool, Enum

if TYPE_CHECKING:
    from typing_extensions import Unpack


class CurrentParameter(MultiParameter):
    """
    Current measurement via an M1b preamplifier module.

    To be used when you feed a current into the M1b, send the M1b's
    output voltage to a voltmeter or other voltage measurement device, and you have
    the voltage reading from that device as a qcodes parameter.

    ``CurrentParameter.get()`` returns ``(voltage_raw, current)``

    Args:
        measured_param: A gettable parameter returning the
            voltage read from the M1b output.
        current_amplifier_instrument: An M1b instance where you manually
            maintain the present settings of the real M1b module.
        name: The name of the current output. Default 'curr'.
            Also used as the name of the whole parameter.
    """

    def __init__(
        self,
        measured_param: Parameter,
        current_amplifier_instrument: "M1b",
        name: str = "curr",
    ):
        parameter_name = measured_param.name

        super().__init__(
            name=name,
            names=(parameter_name + "_raw", name),
            shapes=((), ()),
            setpoints=((), ()),
            instrument=current_amplifier_instrument,
            snapshot_value=True,
        )

        self._measured_param: Parameter = measured_param

        parameter_label = getattr(measured_param, "label", "")
        parameter_unit = getattr(measured_param, "unit", "")

        self.labels = (parameter_label, "Current")
        self.units = (parameter_unit, "A")

    def get_raw(self) -> tuple[ParamRawDataType, ...]:
        """
        Get raw values from the M1b preamplifier.

        Returns:
            Tuple of (voltage_raw, current) where current is calculated
            from voltage using the total gain.
        """
        assert isinstance(self.instrument, M1b)
        voltage = self._measured_param.get()

        # Calculate current from voltage and total gain
        total_gain = self.instrument.total_gain()
        current = voltage / total_gain
        value = (voltage, current)
        return value


class M1b(Instrument):
    """
    QCoDeS driver for the QuTech M1b Current-preamplifier module for IVVI rack.

    This is a virtual driver only and will not talk to your instrument.

    The M1b is a low-noise current-to-voltage converter (transimpedance amplifier)
    designed for use in the IVVI rack system.

    Note that, as this is a purely virtual driver, it is the responsibility of
    the user to ensure that values set here are in accordance with the values
    set on the physical instrument.

    Documentation: https://qtwork.tudelft.nl/~schouten/ivvi/doc-mod/docm1b.htm

    Args:
        name: Name of the instrument instance.
        **kwargs: Forwarded to base class.
    """

    def __init__(self, name: str, **kwargs: "Unpack[InstrumentBaseKWArgs]"):
        super().__init__(name, **kwargs)

        self.slot: ManualParameter = self.add_parameter(
            "slot",
            parameter_class=ManualParameter,
            initial_value="Ma",
            label="Module slot",
            vals=Enum("Ma", "Mb"),
            docstring="Physical slot: Ma (iso-out 1, top) or Mb (iso-out 2, bottom)",
        )
        """Parameter slot"""

        self.gain: ManualParameter = self.add_parameter(
            "gain",
            parameter_class=ManualParameter,
            initial_value="1G",
            label="Transimpedance gain",
            unit="V/A",
            vals=Enum("1M", "10M", "100M", "1G"),
            docstring="Current to voltage conversion gain setting",
        )
        """Parameter gain"""

        self.postgain: ManualParameter = self.add_parameter(
            "postgain",
            parameter_class=ManualParameter,
            initial_value="x1",
            label="Postgain",
            vals=Enum("x1", "x100ac", "x100dc"),
            docstring=(
                "Postgain setting:\n"
                "  x1: No postgain (default)\n"
                "  x100ac: 100x AC coupled gain (for noise measurements with DC offset)\n"
                "  x100dc: 100x DC coupled gain (maximum 100G V/A total)"
            ),
        )
        """Parameter postgain"""

        self.input_resistance_setting: ManualParameter = self.add_parameter(
            "input_resistance_setting",
            parameter_class=ManualParameter,
            initial_value="Low Noise",
            label="Input resistance setting",
            vals=Enum("Low Rin", "Low Noise"),
            docstring="Input resistance mode (function of V/A setting)",
        )
        """Parameter input_resistance_setting"""

        self.reference: ManualParameter = self.add_parameter(
            "reference",
            parameter_class=ManualParameter,
            initial_value="ground",
            label="Reference",
            vals=Enum("ground", "ref-in"),
            docstring=(
                "Reference connection:\n"
                "  ground: Referenced to ground\n"
                "  ref-in: Referenced to external ref-in, ideally a cold ground"
            ),
        )
        """Parameter reference"""

        self.muted: ManualParameter = self.add_parameter(
            "muted",
            parameter_class=ManualParameter,
            initial_value=False,
            label="Mute status",
            vals=Bool(),
            docstring="Whether the output is muted",
        )
        """Parameter muted"""

        # Derived parameters
        self.total_gain: Parameter = self.add_parameter(
            "total_gain",
            label="Total gain",
            unit="V/A",
            get_cmd=self._get_total_gain,
            docstring="Total transimpedance gain including postgain",
        )
        """Parameter total_gain"""

        self.input_resistance: Parameter = self.add_parameter(
            "input_resistance",
            label="Input resistance",
            unit="Ohm",
            get_cmd=self._get_input_resistance,
            docstring="Calculated input resistance based on gain and resistance setting",
        )
        """Parameter input_resistance"""

    def _get_total_gain(self) -> float:
        """
        Calculate total transimpedance gain including postgain.

        Returns:
            Total gain in V/A.
        """
        # Gain mapping in V/A
        gain_map = {
            "1M": 1e6,
            "10M": 1e7,
            "100M": 1e8,
            "1G": 1e9,
        }

        # Postgain factors
        postgain_map = {
            "x1": 1,
            "x100ac": 100,
            "x100dc": 100,
        }

        base_gain = gain_map[self.gain()]
        postgain_factor = postgain_map[self.postgain()]

        return base_gain * postgain_factor

    def _get_input_resistance(self) -> float:
        """
        Calculate input resistance based on transimpedance gain setting.

        From M1b documentation: Rin is a function of the V/A setting.
        Higher V/A → higher Rin

        Returns:
            Input resistance in Ohms.
        """
        # Gain mapping in V/A
        gain_map = {
            "1M": 1e6,
            "10M": 1e7,
            "100M": 1e8,
            "1G": 1e9,
        }

        base_gain = gain_map[self.gain()]

        if self.input_resistance_setting() == "Low Rin":
            additional_resistance = 1e-4 * base_gain
        elif self.input_resistance_setting() == "Low Noise":
            additional_resistance = 1e-3 * base_gain
        else:
            raise ValueError("Invalid input resistance setting")

        # Base resistance of 2kΩ plus additional resistance
        return 2000 + additional_resistance

    def get_idn(self) -> dict[str, str | None]:
        """
        Return the identification of the instrument.

        Returns:
            Dictionary with vendor, model, serial, and firmware information.
        """
        vendor = "QuTech"
        model = "M1b"
        serial = None
        firmware = None
        return {
            "vendor": vendor,
            "model": model,
            "serial": serial,
            "firmware": firmware,
        }
