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
    Voltage measurement via an M2m preamplifier module.

    To be used when you feed a voltage into the M2m, send the M2m's
    output voltage to a voltmeter or other voltage measurement device, and you have
    the voltage reading from that device as a qcodes parameter.

    ``VoltageParameter.get()`` returns ``(voltage_raw, voltage)``

    Args:
        measured_param: A gettable parameter returning the
            voltage read from the M2m output.
        voltage_amplifier_instrument: An M2m instance where you manually
            maintain the present settings of the real M2m module.
        name: The name of the voltage output. Default 'voltage'.
            Also used as the name of the whole parameter.
    """

    def __init__(
        self,
        measured_param: Parameter,
        voltage_amplifier_instrument: "M2m",
        name: str = "voltage",
    ) -> None:

        """
        Wrap a measured voltage parameter to expose both the raw reading and the amplifier-corrected voltage as a two-field MultiParameter.
        
        Parameters:
            measured_param (Parameter): A gettable parameter that provides the raw voltage reading from the amplifier output.
            voltage_amplifier_instrument (M2m): The M2m virtual amplifier instrument whose total gain will be used to compute the corrected voltage.
            name (str): Public name for the corrected voltage sub-parameter; the raw sub-parameter name is derived from `measured_param.name` and suffixed with `_raw`.
        """
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
        Return the raw measured voltage and the calculated output voltage corrected by the instrument gain.
        
        Returns:
            A tuple (voltage_raw, voltage) where `voltage_raw` is the value read from the wrapped measured parameter and `voltage` is `voltage_raw` divided by the instrument's total gain.
        
        Raises:
            TypeError: If `self.instrument` is not an instance of M2m.
        """
        if not isinstance(self.instrument, M2m):
            raise TypeError(f"Expected M2m instrument, got {type(self.instrument)}")
        voltage_raw = self._measured_param.get()

        # Calculate voltage from voltage_raw and total gain
        total_gain = self.instrument.total_gain()
        voltage = voltage_raw / total_gain
        value = (voltage_raw, voltage)
        return value


class M2m(Instrument):
    """
    QCoDeS driver for the QuTech M2m voltage-preamplifier module for IVVI rack.

    This is a virtual driver only and will not talk to your instrument.

    The M2m is a voltage-to-voltage converter (amplifier) designed for use in the IVVI rack system.

    Note that, as this is a purely virtual driver, it is the responsibility of
    the user to ensure that values set here are in accordance with the values
    set on the physical instrument.

    Documentation: https://qtwork.tudelft.nl/~schouten/ivvi/doc-mod/docm2m.htm

    Args:
        name: Name of the instrument instance.
        **kwargs: Forwarded to base class.
    """

    def __init__(self, name: str, **kwargs: "Unpack[InstrumentBaseKWArgs]") -> None:
        """
        Initialize the M2m virtual instrument and register its configuration and derived parameters.
        
        This constructor registers the manual configuration parameters `slot` (module slot, "Ma" or "Mb"), `gain` (amplifier gain setting: "1", "10", "100", "1k", "10k"), and `dc_ac_mode` (coupling mode: "dc", "ac", "hpf"), and it adds the derived read-only parameter `total_gain` that reports the computed voltage gain.
         
        Parameters:
            name: Instrument name used by the base Instrument class.
            **kwargs: Additional keyword arguments forwarded to the base Instrument constructor.
        """
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
            initial_value="1",
            label="Gain",
            unit="V/V",
            vals=Enum("1", "10", "100", "1k", "10k"),
            docstring="Voltage to voltage conversion gain setting",
        )
        """Parameter gain"""

        self.dc_ac_mode: ManualParameter = self.add_parameter(
            "dc_ac_mode",
            parameter_class=ManualParameter,
            initial_value="ac",
            label="DC/AC mode",
            vals=Enum("dc", "ac", "hpf"),
            docstring="Selects DC or AC coupling mode. Optionally this module has a high-pass filter (hpf) mode.",
        )
        """Parameter dc_ac_mode"""

        # Derived parameters
        self.total_gain: Parameter = self.add_parameter(
            "total_gain",
            label="Total gain",
            unit="V/V",
            get_cmd=self._get_total_gain,
            docstring="Total voltage gain computed from base gain setting",
        )
        """Parameter total_gain"""

    def _get_total_gain(self) -> float:
        """
        Compute the total voltage gain (V/V) based on the instrument's current `gain` setting.
        
        The returned value corresponds to the numeric V/V factor for the instrument's `gain` parameter (supported settings: "1", "10", "100", "1k", "10k").
        
        Returns:
            total_gain (float): Total gain in volts per volt (V/V).
        """
        # Gain mapping in V/V
        gain_map = {"1": 1, "10": 10, "100": 100, "1k": 1e3, "10k": 1e4}

        base_gain = gain_map[self.gain()]

        return base_gain

    def get_idn(self) -> dict[str, str | None]:
        """
        Provide identification metadata for the instrument.
        
        @returns
            dict: Mapping with keys 'vendor', 'model', 'serial', and 'firmware'. The 'serial' and 'firmware' values may be None.
        """
        vendor = "QuTech"
        model = "M2m"
        serial = None
        firmware = None
        return {
            "vendor": vendor,
            "model": model,
            "serial": serial,
            "firmware": firmware,
        }