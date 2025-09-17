"""
Abstract base classes for signal chain components.

These define the contracts for modular signal chain elements that can be
composed into complex measurement topologies.
"""

from abc import ABC, abstractmethod
from typing import Optional
from qcodes.instrument import Instrument


class AbstractSource(Instrument, ABC):
    """Abstract voltage or current source.
    
    Defines the contract for AC/DC sources that provide programmable
    output levels and frequencies.
    """
    
    @abstractmethod
    def __init__(self, name: str, **kwargs):
        """Initialize source with standard parameters."""
        super().__init__(name, **kwargs)
        # Expected parameters: output_on, level, frequency (if AC)
    

class AbstractConverter(Instrument, ABC):
    """Abstract voltage-to-current converter.
    
    Defines the contract for devices that convert voltage to current
    with manual transconductance settings.
    """
    
    @abstractmethod
    def __init__(self, name: str, **kwargs):
        """Initialize converter with manual parameters."""
        super().__init__(name, **kwargs)
        # Expected ManualParameters: gm_a_per_v, invert, optional phase_deg, primary_impedance_ohm


class AbstractAmplifier(Instrument, ABC):
    """Abstract voltage amplifier.
    
    Defines the contract for voltage-to-voltage amplifiers with
    manual gain settings.
    """
    
    @abstractmethod
    def __init__(self, name: str, **kwargs):
        """Initialize amplifier with manual parameters."""
        super().__init__(name, **kwargs)
        # Expected ManualParameters: gain_v_per_v, invert, optional coupling, bandwidth_hz


class AbstractLockIn(Instrument, ABC):
    """Abstract lock-in amplifier.
    
    Defines the contract for lock-in amplifiers with demodulation
    and readout capabilities.
    """
    
    @abstractmethod
    def __init__(self, name: str, **kwargs):
        """Initialize lock-in with standard parameters."""
        super().__init__(name, **kwargs)
        # Expected parameters: frequency, time_constant, sensitivity, input_range
        # Expected readouts: X, Y, R, Theta