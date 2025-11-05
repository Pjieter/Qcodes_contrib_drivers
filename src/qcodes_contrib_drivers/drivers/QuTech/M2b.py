from typing import TYPE_CHECKING

from qcodes.instrument import Instrument, InstrumentBaseKWArgs
from qcodes.parameters import (
    ManualParameter,
    MultiParameter,
    Parameter,
    ParamRawDataType,
)
from qcodes.validators import Enum

if TYPE_CHECKING:
    from typing_extensions import Unpack


class VoltageParameter(MultiParameter):
    """
    Voltage measurement via an M2b preamplifier module.

    To be used when you feed a voltage into the M2b, send the M2b's
    output voltage to a voltmeter or other voltage measurement device, and you have
    the voltage reading from that device as a qcodes parameter.

    ``VoltageParameter.get()`` returns ``(voltage_raw, voltage)``

    Args:
        measured_param: A gettable parameter returning the
            voltage read from the M2b output.
        voltage_amplifier_instrument: An M2b instance where you manually
            maintain the present settings of the real M2b module.
        name: The name of the voltage output. Default 'voltage'.
            Also used as the name of the whole parameter.
    """

    def __init__(
        self,
        measured_param: Parameter,
        voltage_amplifier_instrument: "M2b",
        name: str = "voltage",
    ):
        parameter_name = measured_param.name

        super().__init__(
            name=name,
            names=(parameter_name + "_raw", name),
            shapes=((), ()),
            setpoints=((), ()),
            instrument=voltage_amplifier_instrument,
            snapshot_value=True,
        )

        self._measured_param: Parameter = measured_param

        parameter_label = getattr(measured_param, "label", "")
        parameter_unit = getattr(measured_param, "unit", "")

        self.labels = (parameter_label, "voltage")
        self.units = (parameter_unit, "V")

    def get_raw(self) -> tuple[ParamRawDataType, ...]:
        """
        Get raw values from the M2b preamplifier.

        Returns:
            Tuple of (voltage_raw, voltage) where voltage is calculated
            from voltage using the total gain.
        """
        assert isinstance(self.instrument, M2b)
        voltage_raw = self._measured_param.get()

        # Calculate voltage from voltage and total gain
        total_gain = self.instrument.total_gain()
        voltage = voltage_raw / total_gain
        value = (voltage_raw, voltage)
        return value


class M2b(Instrument):
    """
    QCoDeS driver for the QuTech M2b voltage-preamplifier module for IVVI rack.

    This is a virtual driver only and will not talk to your instrument.

    The M2b is a low-noise voltage-to-voltage converter (amplifier)
    designed for use in the IVVI rack system.

    Note that, as this is a purely virtual driver, it is the responsibility of
    the user to ensure that values set here are in accordance with the values
    set on the physical instrument.

    Documentation: https://qtwork.tudelft.nl/~schouten/ivvi/doc-mod/docm2b.htm

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
            initial_value="100",
            label="Gain",
            unit="V/V",
            vals=Enum("100", "1k", "10k"),
            docstring="Voltage to voltage conversion gain setting",
        )
        """Parameter gain"""

        self.dc_ac_mode: ManualParameter = self.add_parameter(
            "dc_ac_mode",
            parameter_class=ManualParameter,
            initial_value="ac",
            label="DC/AC mode",
            vals=Enum("dc", "ac"),
            docstring="Parameter dc_ac_mode — selects DC or AC coupling mode",
        )
        """Parameter dc_ac_mode"""

        # Derived parameters
        self.total_gain: Parameter = self.add_parameter(
            "total_gain",
            label="Total gain",
            unit="V/V",
            get_cmd=self._get_total_gain,
            docstring="Total gain",
        )
        """Parameter total_gain"""

    def _get_total_gain(self) -> float:
        """
        Calculate total voltage gain (V/V).

        Note: Currently returns only the base gain from the gain mapping.
        Postgain is not implemented.

        Returns:
            Total gain in V/V.
        """
        # Gain mapping in V/V
        gain_map = {"100": 100, "1k": 1e3, "10k": 1e4}

        base_gain = gain_map[self.gain()]

        return base_gain

    def get_idn(self) -> dict[str, str | None]:
        """
        Return the identification of the instrument.

        Returns:
            Dictionary with vendor, model, serial, and firmware information.
        """
        vendor = "QuTech"
        model = "M2b"
        serial = None
        firmware = None
        return {
            "vendor": vendor,
            "model": model,
            "serial": serial,
            "firmware": firmware,
        }
