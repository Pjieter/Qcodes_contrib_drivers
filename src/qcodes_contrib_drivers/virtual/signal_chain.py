"""SignalChain virtual instrument for IVVI_rack topology."""

import warnings
from typing import Optional, Union, Any
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

from ..nodes.abstract_bases import AbstractSource, AbstractConverter, AbstractAmplifier, AbstractLockIn


class SignalChain(Instrument):
    """Virtual instrument representing the complete IVVI_rack signal chain.
    
    Topology: [MFLI Source] → [V→I Transformer] → [Sample] → [Voltage Preamp] → [MFLI Lock-in]
    
    This instrument flattens the control interface and provides derived physics parameters,
    with a single current setpoint parameter (I_set) that computes the required source voltage.
    """
    
    def __init__(
        self, 
        src_v: AbstractSource,
        vi: AbstractConverter, 
        preamp: AbstractAmplifier,
        lockin: AbstractLockIn,
        name: str = "signal_chain",
        **kwargs
    ):
        """Initialize signal chain with device nodes.
        
        Args:
            src_v: MFLI source for AC voltage excitation
            vi: Manual V→I transformer (manual transconductance)
            preamp: Manual voltage preamplifier (flat V/V)
            lockin: MFLI lock-in for input & demodulation
            name: Name for this virtual instrument
        """
        try:
            super().__init__(name, **kwargs)
        except TypeError:
            # Fallback for testing without QCoDeS
            self.name = name
        self.src_v = src_v
        self.vi = vi
        self.preamp = preamp
        self.lockin = lockin
        
        # Delegate programmable parameters (flatten interface)
        self.add_parameter(
            "excitation_v_ac", 
            parameter_class=DelegateParameter,
            source=src_v.level,
            label="Excitation voltage (RMS)",
            unit="V",
            docstring="RMS amplitude of AC voltage source"
        )
        
        self.add_parameter(
            "output_on",
            parameter_class=DelegateParameter, 
            source=src_v.output_on,
            label="Source output enable",
            docstring="Enable/disable source output"
        )
        
        # Lock-in parameters
        for param_name in ["time_constant", "sensitivity", "input_range"]:
            self.add_parameter(
                param_name,
                parameter_class=DelegateParameter,
                source=getattr(lockin, param_name),
                label=param_name.replace("_", " ").title(),
                docstring=f"Lock-in {param_name.replace('_', ' ')}"
            )
        
        # Lock-in readouts
        for param_name in ["X", "Y", "R", "Theta"]:
            self.add_parameter(
                param_name,
                parameter_class=DelegateParameter,
                source=getattr(lockin, param_name),
                label=f"{param_name} readout",
                docstring=f"Lock-in {param_name} component"
            )
        
        # Manual device parameters
        self.add_parameter(
            "gm_a_per_v",
            parameter_class=DelegateParameter,
            source=vi.gm_a_per_v,
            label="Transconductance",
            unit="A/V",
            docstring="V→I transformer transconductance (A/V, RMS)"
        )
        
        self.add_parameter(
            "vi_invert",
            parameter_class=DelegateParameter,
            source=vi.invert,
            label="V→I invert",
            docstring="V→I transformer signal inversion"
        )
        
        self.add_parameter(
            "preamp_gain",
            parameter_class=DelegateParameter,
            source=preamp.gain_v_per_v,
            label="Preamp gain", 
            unit="V/V",
            docstring="Voltage preamplifier gain (V/V)"
        )
        
        self.add_parameter(
            "preamp_invert",
            parameter_class=DelegateParameter,
            source=preamp.invert,
            label="Preamp invert",
            docstring="Voltage preamplifier signal inversion"
        )
        
        # Coupled frequency parameter
        def _set_ref_freq(f: float):
            """Set both source and lock-in frequency."""
            if hasattr(self.src_v, 'frequency') and self.src_v.frequency is not None:
                self.src_v.frequency.set(f)
            self.lockin.frequency.set(f)
            
        def _get_ref_freq() -> float:
            """Get lock-in frequency as reference."""
            return float(self.lockin.frequency())
        
        self.add_parameter(
            "reference_frequency",
            unit="Hz",
            set_cmd=_set_ref_freq,
            get_cmd=_get_ref_freq,
            vals=Numbers(min_value=0),
            label="Reference frequency",
            docstring="Coupled frequency for both source and lock-in"
        )
        
        # Manual advisory parameters
        self.add_parameter(
            "R_est",
            parameter_class=ManualParameter,
            initial_value=None,
            unit="Ω",
            vals=Numbers(min_value=0),
            label="Estimated resistance",
            docstring="Manual estimate of sample resistance for I_meas calculation"
        )
        
        self.add_parameter(
            "margin", 
            parameter_class=ManualParameter,
            initial_value=3.0,
            vals=Numbers(min_value=1),
            label="Safety margin",
            docstring="Safety margin factor for guard calculations"
        )
        
        self.add_parameter(
            "amplitude_convention",
            parameter_class=ManualParameter,
            initial_value="rms",
            vals=Enum("rms", "amp", "pp"),
            label="Amplitude convention",
            docstring="Amplitude convention: RMS, amplitude, or peak-to-peak"
        )
        
        # Current setpoint with open-loop control
        def _set_I_target(I_target: float):
            """Set target current by computing required source voltage."""
            gm_eff = self._gm_eff()
            if gm_eff == 0:
                raise ValueError("gm_a_per_v is zero; cannot compute source voltage.")
            
            V_needed = I_target / gm_eff
            
            # Optional guard check
            self._guard_lockin_overload(I_target)
            
            # Set source voltage and ensure output is on
            self.excitation_v_ac.set(V_needed)
            self.output_on.set(True)
        
        def _get_I_cmd() -> float:
            """Get commanded current based on current source voltage."""
            return self._gm_eff() * float(self.excitation_v_ac())
        
        self.add_parameter(
            "I_set",
            unit="A",
            set_cmd=_set_I_target,
            get_cmd=_get_I_cmd,
            vals=Numbers(),
            label="Current setpoint",
            docstring="Target current setpoint (A) - sets source voltage via gm"
        )
        
        # Derived readback parameters (pure functions, no I/O)
        self.add_parameter(
            "I_cmd",
            unit="A", 
            get_cmd=_get_I_cmd,
            label="Commanded current",
            docstring="Current commanded based on source voltage and gm"
        )
        
        def _get_V_sample_ac_meas() -> complex:
            """Get measured AC voltage at sample (complex).""" 
            X_val = float(self.X())
            Y_val = float(self.Y())
            gv_eff = self._gv_eff()
            if gv_eff == 0:
                return complex(0, 0)
            return complex(X_val, Y_val) / gv_eff
        
        self.add_parameter(
            "V_sample_ac_meas",
            unit="V",
            get_cmd=_get_V_sample_ac_meas,
            label="Measured sample voltage",
            docstring="Measured AC voltage at sample (complex V/V_eff)"
        )
        
        def _get_I_meas() -> Optional[float]:
            """Get measured current based on sample voltage and resistance."""
            R_est = self.R_est()
            if R_est in (None, 0):
                return None
            V_sample = _get_V_sample_ac_meas()
            return abs(V_sample) / float(R_est)
        
        self.add_parameter(
            "I_meas",
            unit="A",
            get_cmd=_get_I_meas,
            label="Measured current", 
            docstring="Measured current |V_sample|/R_est (requires R_est)"
        )
        
        def _get_recommended_sensitivity() -> float:
            """Get recommended sensitivity based on current R measurement."""
            margin = float(self.margin())
            R_val = float(self.R())
            return margin * R_val
        
        self.add_parameter(
            "recommended_sensitivity",
            unit="V",
            get_cmd=_get_recommended_sensitivity,
            label="Recommended sensitivity",
            docstring="Recommended lock-in sensitivity (margin × R)"
        )
    
    def _gm_eff(self) -> float:
        """Effective transconductance including inversion."""
        gm = float(self.gm_a_per_v())
        invert = bool(self.vi_invert())
        return -gm if invert else gm
    
    def _gv_eff(self) -> float:
        """Effective preamp gain including inversion."""
        gv = float(self.preamp_gain())
        invert = bool(self.preamp_invert())
        return -gv if invert else gv
    
    def _guard_lockin_overload(self, I_target: float) -> None:
        """Check for potential lock-in input overload and warn."""
        R_est = self.R_est()
        if R_est in (None, 0):
            return  # Cannot predict without resistance estimate
        
        # Predict preamp output voltage
        V_preamp_out_pred = abs(I_target) * float(R_est) * abs(self._gv_eff())
        
        # Check against input range
        input_range = float(self.input_range())
        threshold = 0.8 * input_range
        
        if V_preamp_out_pred > threshold:
            warnings.warn(
                f"[GUARD] Predicted lock-in input {V_preamp_out_pred:.3g} V "
                f"exceeds 80% of input range {input_range:.3g} V. "
                f"Consider reducing current or increasing input range.",
                UserWarning
            )
    
    def get_topology_summary(self) -> str:
        """Get a summary of the signal chain topology and current settings."""
        gm_eff = self._gm_eff()
        gv_eff = self._gv_eff()
        
        summary = f"""
Signal Chain Topology Summary:
==============================
[MFLI Source] → [V→I Transformer] → [Sample] → [Voltage Preamp] → [MFLI Lock-in]

Current Settings:
- Source voltage (RMS): {self.excitation_v_ac()} V
- Output enabled: {self.output_on()}
- Reference frequency: {self.reference_frequency()} Hz
- Effective transconductance: {gm_eff:.3e} A/V
- Effective preamp gain: {gv_eff:.1f} V/V
- Estimated sample resistance: {self.R_est()} Ω

Derived Values:
- Commanded current: {self.I_cmd():.3e} A
- Measured current: {self.I_meas()} A (if R_est set)
- Sample voltage (complex): {self.V_sample_ac_meas()} V
"""
        return summary