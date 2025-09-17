"""Concrete implementations of signal chain nodes."""

from typing import Optional, Any
try:
    from qcodes import Instrument
    from qcodes.parameters import Parameter, ManualParameter, DelegateParameter
    from qcodes.validators import Numbers, Bool, Enum
except ImportError:
    # Fallback for development without QCoDeS installed
    class Instrument:
        def __init__(self, name: str, **kwargs):
            self.name = name
        def add_parameter(self, name: str, **kwargs):
            pass
    class Parameter:
        pass
    class ManualParameter:
        pass
    class DelegateParameter:
        pass
    class Numbers:
        def __init__(self, *args, **kwargs):
            pass
    class Bool:
        pass
    class Enum:
        def __init__(self, *args, **kwargs):
            pass

from .abstract_bases import AbstractSource, AbstractConverter, AbstractAmplifier, AbstractLockIn


class MFLISource(AbstractSource):
    """MFLI source implementation using HF2LI-style interface.
    
    Adapts existing HF2LI driver parameters to provide standard source interface.
    For MFLI compatibility, this would delegate to actual MFLI driver parameters.
    """
    
    def __init__(self, mfli_driver: Any, name: str = "mfli_source", **kwargs):
        """Initialize MFLI source wrapper.
        
        Args:
            mfli_driver: The underlying MFLI/HF2LI driver instance
            name: Name for this source instance
        """
        try:
            super().__init__(name, **kwargs)
        except TypeError:
            # Fallback for testing without QCoDeS - just set the name
            self.name = name
        self._mfli = mfli_driver
        
        # Delegate to MFLI driver parameters
        # Assuming MFLI has sigout_amplitude0 and sigout_enable0 parameters like HF2LI
        self.add_parameter(
            "amplitude",
            parameter_class=DelegateParameter,
            source=getattr(mfli_driver, 'sigout_amplitude0', None) or self._create_dummy_param("amplitude"),
            label="Source amplitude",
            unit="V",
            docstring="RMS amplitude of AC voltage source"
        )
        
        self.add_parameter(
            "output_on", 
            parameter_class=DelegateParameter,
            source=getattr(mfli_driver, 'sigout_enable0', None) or self._create_dummy_param("output_on"),
            label="Output enable",
            docstring="Enable/disable source output"
        )
        
        self.add_parameter(
            "frequency",
            parameter_class=DelegateParameter,
            source=getattr(mfli_driver, 'frequency', None) or self._create_dummy_param("frequency"),
            label="Source frequency",
            unit="Hz",
            docstring="AC frequency of source"
        )
        
        # Alias for standard interface
        self.level = self.amplitude
    
    def _create_dummy_param(self, name: str) -> Parameter:
        """Create dummy parameter for testing without real hardware."""
        return Parameter(
            name=name,
            instrument=self,
            get_cmd=None,
            set_cmd=None,
            initial_value=0.0
        )


class ManualVITransformer(AbstractConverter):
    """Manual V→I transformer with transconductance and inversion settings."""
    
    def __init__(self, name: str = "vi_transformer", **kwargs):
        try:
            super().__init__(name, **kwargs)
        except TypeError:
            # Fallback for testing without QCoDeS
            self.name = name
        
        self.add_parameter(
            "gm_a_per_v",
            parameter_class=ManualParameter,
            initial_value=1e-3,  # Default 1 mA/V
            unit="A/V",
            vals=Numbers(min_value=0),
            label="Transconductance", 
            docstring="Transconductance in A/V (RMS)"
        )
        
        self.add_parameter(
            "invert",
            parameter_class=ManualParameter,
            initial_value=False,
            vals=Bool(),
            label="Invert signal",
            docstring="Whether to invert the signal"
        )
        
        self.add_parameter(
            "phase_deg",
            parameter_class=ManualParameter,
            initial_value=0.0,
            unit="deg",
            vals=Numbers(-180, 180),
            label="Phase shift",
            docstring="Optional phase shift in degrees"
        )
        
        self.add_parameter(
            "primary_impedance_ohm", 
            parameter_class=ManualParameter,
            initial_value=None,
            unit="Ω",
            vals=Numbers(min_value=0),
            label="Primary impedance",
            docstring="Optional primary impedance in Ω"
        )


class ManualVoltagePreamp(AbstractAmplifier):
    """Manual voltage preamplifier with gain and inversion settings."""
    
    def __init__(self, name: str = "voltage_preamp", **kwargs):
        try:
            super().__init__(name, **kwargs)
        except TypeError:
            # Fallback for testing without QCoDeS
            self.name = name
        
        self.add_parameter(
            "gain_v_per_v",
            parameter_class=ManualParameter,
            initial_value=100.0,  # Default 100 V/V
            unit="V/V",
            vals=Numbers(min_value=0),
            label="Voltage gain",
            docstring="Voltage gain in V/V"
        )
        
        self.add_parameter(
            "invert",
            parameter_class=ManualParameter,
            initial_value=False,
            vals=Bool(),
            label="Invert signal",
            docstring="Whether to invert the signal"
        )
        
        self.add_parameter(
            "coupling",
            parameter_class=ManualParameter,
            initial_value="AC",
            vals=Enum("AC", "DC"),
            label="Input coupling",
            docstring="Input coupling type"
        )
        
        self.add_parameter(
            "bandwidth_hz",
            parameter_class=ManualParameter,
            initial_value=None,
            unit="Hz",
            vals=Numbers(min_value=0),
            label="Bandwidth",
            docstring="Optional bandwidth in Hz"
        )


class MFLILockIn(AbstractLockIn):
    """MFLI lock-in implementation using HF2LI-style interface.
    
    Adapts existing HF2LI driver parameters to provide standard lock-in interface.
    """
    
    def __init__(self, mfli_driver: Any, name: str = "mfli_lockin", **kwargs):
        """Initialize MFLI lock-in wrapper.
        
        Args:
            mfli_driver: The underlying MFLI/HF2LI driver instance
            name: Name for this lock-in instance
        """
        try:
            super().__init__(name, **kwargs)
        except TypeError:
            # Fallback for testing without QCoDeS
            self.name = name
        self._mfli = mfli_driver
        
        # Delegate to MFLI driver parameters
        self.add_parameter(
            "frequency",
            parameter_class=DelegateParameter,
            source=getattr(mfli_driver, 'frequency', None) or self._create_dummy_param("frequency"),
            label="Demod frequency",
            unit="Hz"
        )
        
        self.add_parameter(
            "time_constant",
            parameter_class=DelegateParameter,
            source=getattr(mfli_driver, 'time_constant', None) or self._create_dummy_param("time_constant"),
            label="Time constant",
            unit="s"
        )
        
        # For HF2LI compatibility, sensitivity might be handled differently
        self.add_parameter(
            "sensitivity",
            parameter_class=DelegateParameter,
            source=getattr(mfli_driver, 'sensitivity', None) or self._create_dummy_param("sensitivity"),
            label="Input sensitivity"
        )
        
        self.add_parameter(
            "input_range",
            parameter_class=DelegateParameter,
            source=getattr(mfli_driver, 'sigout_range', None) or self._create_dummy_param("input_range"),
            label="Input range",
            unit="V"
        )
        
        # Readout parameters - assuming HF2LI has X, Y, R, Theta parameters
        for param_name in ['X', 'Y', 'R', 'Theta']:
            self.add_parameter(
                param_name,
                parameter_class=DelegateParameter,
                source=getattr(mfli_driver, param_name, None) or self._create_dummy_param(param_name),
                label=f"{param_name} readout",
                unit="V" if param_name in ['X', 'Y', 'R'] else "deg"
            )
    
    def _create_dummy_param(self, name: str) -> Parameter:
        """Create dummy parameter for testing without real hardware."""
        return Parameter(
            name=name,
            instrument=self,
            get_cmd=None,
            set_cmd=None,
            initial_value=0.0
        )