"""
SignalChain virtual instrument for IVVI rack topology.

This implements a virtual instrument that provides a high-level interface
for controlling the signal chain topology:
[MFLI AC Voltage Source] → [Manual V→I Transformer] → [Sample] → [Manual Voltage Preamp] → [MFLI Input & Demod]
"""

import numpy as np
from typing import Optional, Union
import qcodes.validators as vals
from qcodes.instrument import Instrument
from qcodes.parameters import ManualParameter, DelegateParameter, Parameter


class SignalChain(Instrument):
    """
    Virtual instrument for IVVI rack signal chain with current setpoint control.
    
    Provides high-level control over the signal chain topology with:
    - Single current setpoint parameter (I_set) with open-loop control
    - Frequency coupling between source and demod
    - Guard functions for input range protection
    - Derived physics parameters
    """
    
    def __init__(self, src_v, vi_transformer, preamp, lockin, name="signal_chain", **kwargs):
        """
        Initialize signal chain.
        
        Args:
            src_v: MFLISource instance
            vi_transformer: ManualVITransformer instance
            preamp: ManualVoltagePreamp instance  
            lockin: MFLILockIn instance
            name: Name of the virtual instrument
        """
        super().__init__(name, **kwargs)
        self.src_v = src_v
        self.vi = vi_transformer
        self.preamp = preamp
        self.lockin = lockin

        # Delegates for programmable parameters (flatten the hierarchy)
        self.add_parameter("excitation_v_ac", 
                          parameter_class=DelegateParameter, 
                          source=src_v.amplitude,
                          docstring="AC excitation voltage amplitude (RMS)")
        
        self.add_parameter("output_on", 
                          parameter_class=DelegateParameter, 
                          source=src_v.output_on,
                          docstring="Source output enable")
        
        self.add_parameter("time_constant", 
                          parameter_class=DelegateParameter, 
                          source=lockin.time_constant,
                          docstring="Lock-in time constant")
        
        self.add_parameter("sensitivity", 
                          parameter_class=DelegateParameter, 
                          source=lockin.sensitivity,
                          docstring="Lock-in sensitivity")
        
        self.add_parameter("input_range", 
                          parameter_class=DelegateParameter, 
                          source=lockin.input_range,
                          docstring="Lock-in input range")
        
        # Readout delegates (if they exist on the lock-in)
        if hasattr(lockin, 'X'):
            self.add_parameter("X", 
                              parameter_class=DelegateParameter, 
                              source=lockin.X,
                              docstring="X readout")
        if hasattr(lockin, 'Y'):
            self.add_parameter("Y", 
                              parameter_class=DelegateParameter, 
                              source=lockin.Y,
                              docstring="Y readout")
        if hasattr(lockin, 'R'):
            self.add_parameter("R", 
                              parameter_class=DelegateParameter, 
                              source=lockin.R,
                              docstring="R readout")
        if hasattr(lockin, 'Theta'):
            self.add_parameter("Theta", 
                              parameter_class=DelegateParameter, 
                              source=lockin.Theta,
                              docstring="Theta readout")

        # Manual parameter delegates
        self.add_parameter("gm_a_per_v", 
                          parameter_class=DelegateParameter, 
                          source=vi_transformer.gm_a_per_v,
                          docstring="V-I transformer transconductance")
        
        self.add_parameter("vi_invert", 
                          parameter_class=DelegateParameter, 
                          source=vi_transformer.invert,
                          docstring="V-I transformer polarity invert")
        
        self.add_parameter("preamp_gain", 
                          parameter_class=DelegateParameter, 
                          source=preamp.gain_v_per_v,
                          docstring="Preamp voltage gain")
        
        self.add_parameter("preamp_invert", 
                          parameter_class=DelegateParameter, 
                          source=preamp.invert,
                          docstring="Preamp polarity invert")

        # Frequency coupling parameter
        def _set_ref_freq(f: float):
            """Set frequency on both source and lock-in."""
            self.src_v.frequency.set(f)
            self.lockin.frequency.set(f)
            
        def _get_ref_freq():
            """Get frequency from lock-in (assumed to be the reference)."""
            return self.lockin.frequency()
            
        self.add_parameter("reference_frequency", 
                          unit="Hz", 
                          set_cmd=_set_ref_freq, 
                          get_cmd=_get_ref_freq,
                          vals=vals.Numbers(min_value=1e-3, max_value=5e6),
                          docstring="Reference frequency (couples source and demod)")

        # Advisory/manual parameters
        self.add_parameter("R_est", 
                          parameter_class=ManualParameter, 
                          unit="Ω", 
                          initial_value=None,
                          vals=vals.Numbers(min_value=0),
                          docstring="Estimated sample resistance")
        
        self.add_parameter("margin", 
                          parameter_class=ManualParameter, 
                          initial_value=3.0, 
                          vals=vals.Numbers(min_value=1),
                          docstring="Safety margin factor for guards")
        
        self.add_parameter("amplitude_convention", 
                          parameter_class=ManualParameter,
                          initial_value="rms", 
                          vals=vals.Enum("rms", "amp", "pp"),
                          docstring="Amplitude convention (RMS, amplitude, peak-to-peak)")

        # Current setpoint with open-loop control via gm
        def _set_I_target(I_target: float):
            """Set target current via open-loop voltage calculation."""
            gm_eff = self._gm_eff()
            if abs(gm_eff) < 1e-15:  # Avoid division by zero
                raise ValueError("gm_a_per_v is zero; cannot compute source voltage.")
            
            V_needed = I_target / gm_eff
            
            # Apply guard function before setting
            self._guard_lockin_overload(I_target)
            
            # Set the source voltage and ensure output is on
            self.excitation_v_ac.set(abs(V_needed))  # Use magnitude for RMS amplitude
            self.output_on.set(True)

        def _get_I_cmd():
            """Get commanded current based on current source settings."""
            return self._gm_eff() * float(self.excitation_v_ac())

        self.add_parameter("I_set", 
                          unit="A", 
                          set_cmd=_set_I_target, 
                          get_cmd=_get_I_cmd, 
                          vals=vals.Numbers(),
                          docstring="Target current setpoint (open-loop via gm)")

        # Derived readback parameters (pure functions, no device I/O)
        self.add_parameter("I_cmd", 
                          unit="A", 
                          get_cmd=_get_I_cmd,
                          docstring="Commanded current based on source settings")
        
        def _get_V_sample_ac_meas():
            """Get measured AC voltage at sample (corrected for preamp gain)."""
            if hasattr(self, 'X') and hasattr(self, 'Y'):
                gv_eff = self._gv_eff()
                if abs(gv_eff) < 1e-15:
                    return complex(0, 0)
                return complex(float(self.X()), float(self.Y())) / gv_eff
            else:
                return None
                
        self.add_parameter("V_sample_ac_meas", 
                          unit="V", 
                          get_cmd=_get_V_sample_ac_meas,
                          docstring="Measured AC voltage at sample (complex)")
        
        def _get_I_meas():
            """Get measured current from V_sample and R_est."""
            R_est = self.R_est()
            if R_est in (None, 0):
                return None
            V_sample = self.V_sample_ac_meas()
            if V_sample is None:
                return None
            return abs(V_sample) / float(R_est)
            
        self.add_parameter("I_meas", 
                          unit="A", 
                          get_cmd=_get_I_meas,
                          docstring="Measured current from V_sample and R_est")
        
        def _get_recommended_sensitivity():
            """Get recommended sensitivity based on current R reading."""
            if hasattr(self, 'R'):
                return float(self.margin()) * float(self.R())
            else:
                return None
                
        self.add_parameter("recommended_sensitivity", 
                          unit="V", 
                          get_cmd=_get_recommended_sensitivity,
                          docstring="Recommended sensitivity based on R and margin")

    def _gm_eff(self) -> float:
        """Get effective transconductance including polarity."""
        gm = float(self.gm_a_per_v())
        return -gm if bool(self.vi_invert()) else gm
    
    def _gv_eff(self) -> float:
        """Get effective preamp gain including polarity."""
        gv = float(self.preamp_gain())
        return -gv if bool(self.preamp_invert()) else gv
    
    def _guard_lockin_overload(self, I_target: float):
        """Guard function to warn about potential lock-in input overload."""
        R_est = self.R_est()
        if R_est in (None, 0):
            return  # Cannot predict without R_est
            
        # Predict voltage at preamp output
        V_preamp_out_pred = abs(I_target) * float(R_est) * abs(self._gv_eff())
        
        # Check against input range
        try:
            input_range = float(self.input_range())
            threshold = 0.8 * input_range
            
            if V_preamp_out_pred > threshold:
                print(f"[guard] Predicted lock-in input {V_preamp_out_pred:.3g} V "
                      f"exceeds 80% of input range {input_range:.3g} V.")
        except Exception:
            # If we can't get input_range, skip the guard
            pass