"""
Concrete node implementations for signal chain components.

These implement the abstract base classes for specific devices
and manual components in the signal chain.
"""

from typing import Optional, Union
import qcodes.validators as vals
from qcodes.parameters import ManualParameter, DelegateParameter
from ..virtual.signal_chain_abstracts import AbstractSource, AbstractConverter, AbstractAmplifier, AbstractLockIn


class MFLISource(AbstractSource):
    """MFLI source node that delegates to MFLI driver oscillator parameters."""
    
    def __init__(self, name: str, mfli_instrument, **kwargs):
        """
        Initialize MFLI source node.
        
        Args:
            name: Name of the source node
            mfli_instrument: Instance of MFLI driver instrument
        """
        super().__init__(name, **kwargs)
        self.mfli = mfli_instrument
        
        # Delegate to MFLI parameters with consistent naming
        self.add_parameter('amplitude', 
                          parameter_class=DelegateParameter, 
                          source=mfli_instrument.amplitude,
                          docstring='RMS amplitude in volts')
        
        self.add_parameter('frequency', 
                          parameter_class=DelegateParameter, 
                          source=mfli_instrument.frequency,
                          docstring='Output frequency in Hz')
        
        self.add_parameter('output_on', 
                          parameter_class=DelegateParameter, 
                          source=mfli_instrument.output_on,
                          docstring='Output enable state')


class ManualVITransformer(AbstractConverter):
    """Manual voltage-to-current transformer node."""
    
    def __init__(self, name: str, **kwargs):
        """
        Initialize manual V-I transformer.
        
        Args:
            name: Name of the transformer node
        """
        super().__init__(name, **kwargs)
        
        self.add_parameter('gm_a_per_v',
                          parameter_class=ManualParameter,
                          initial_value=1e-3,
                          unit='A/V',
                          vals=vals.Numbers(min_value=0),
                          docstring='Transconductance in A/V (RMS)')
        
        self.add_parameter('invert',
                          parameter_class=ManualParameter,
                          initial_value=False,
                          vals=vals.Bool(),
                          docstring='Whether the transformer inverts polarity')
        
        # Optional parameters for future use
        self.add_parameter('phase_deg',
                          parameter_class=ManualParameter,
                          initial_value=0.0,
                          unit='deg',
                          vals=vals.Numbers(-180, 180),
                          docstring='Phase shift in degrees (optional)')
        
        self.add_parameter('primary_impedance_ohm',
                          parameter_class=ManualParameter,
                          initial_value=None,
                          unit='Ω',
                          vals=vals.Numbers(min_value=0),
                          docstring='Primary impedance in ohms (optional)')


class ManualVoltagePreamp(AbstractAmplifier):
    """Manual voltage preamplifier node."""
    
    def __init__(self, name: str, **kwargs):
        """
        Initialize manual voltage preamp.
        
        Args:
            name: Name of the preamp node
        """
        super().__init__(name, **kwargs)
        
        self.add_parameter('gain_v_per_v',
                          parameter_class=ManualParameter,
                          initial_value=100.0,
                          unit='V/V',
                          vals=vals.Numbers(min_value=0),
                          docstring='Voltage gain in V/V')
        
        self.add_parameter('invert',
                          parameter_class=ManualParameter,
                          initial_value=False,
                          vals=vals.Bool(),
                          docstring='Whether the preamp inverts polarity')
        
        # Optional parameters for future use
        self.add_parameter('coupling',
                          parameter_class=ManualParameter,
                          initial_value='AC',
                          vals=vals.Enum('AC', 'DC'),
                          docstring='Input coupling (optional)')
        
        self.add_parameter('bandwidth_hz',
                          parameter_class=ManualParameter,
                          initial_value=None,
                          unit='Hz',
                          vals=vals.Numbers(min_value=0),
                          docstring='Bandwidth in Hz (optional)')


class MFLILockIn(AbstractLockIn):
    """MFLI lock-in node that delegates to MFLI driver demod parameters."""
    
    def __init__(self, name: str, mfli_instrument, **kwargs):
        """
        Initialize MFLI lock-in node.
        
        Args:
            name: Name of the lock-in node
            mfli_instrument: Instance of MFLI driver instrument
        """
        super().__init__(name, **kwargs)
        self.mfli = mfli_instrument
        
        # Delegate to MFLI demod parameters
        self.add_parameter('frequency', 
                          parameter_class=DelegateParameter, 
                          source=mfli_instrument.frequency,
                          docstring='Demodulation frequency in Hz')
        
        self.add_parameter('time_constant', 
                          parameter_class=DelegateParameter, 
                          source=mfli_instrument.time_constant,
                          docstring='Time constant in seconds')
        
        self.add_parameter('sensitivity', 
                          parameter_class=DelegateParameter, 
                          source=mfli_instrument.sensitivity,
                          docstring='Input sensitivity in V')
        
        self.add_parameter('input_range', 
                          parameter_class=DelegateParameter, 
                          source=mfli_instrument.input_range,
                          docstring='Input range in V')
        
        # Delegate readout parameters - these should exist on the MFLI instrument
        # Check if they exist, if not we'll need to add them
        if hasattr(mfli_instrument, 'X'):
            self.add_parameter('X', 
                              parameter_class=DelegateParameter, 
                              source=mfli_instrument.X,
                              docstring='X readout in V')
        
        if hasattr(mfli_instrument, 'Y'):
            self.add_parameter('Y', 
                              parameter_class=DelegateParameter, 
                              source=mfli_instrument.Y,
                              docstring='Y readout in V')
        
        if hasattr(mfli_instrument, 'R'):
            self.add_parameter('R', 
                              parameter_class=DelegateParameter, 
                              source=mfli_instrument.R,
                              docstring='R readout in V')
        
        if hasattr(mfli_instrument, 'Theta'):
            self.add_parameter('Theta', 
                              parameter_class=DelegateParameter, 
                              source=mfli_instrument.Theta,
                              docstring='Theta readout in degrees')