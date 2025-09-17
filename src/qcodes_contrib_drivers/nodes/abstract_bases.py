"""Abstract base classes for modular signal chain components."""

from abc import ABC, abstractmethod
from typing import Optional
try:
    from qcodes import Instrument
    from qcodes.parameters import Parameter
except ImportError:
    # Fallback for development without QCoDeS installed
    class Instrument:
        pass
    class Parameter:
        pass


class AbstractSource(Instrument, ABC):
    """Abstract base class for voltage or current sources.
    
    Provides interface for AC/DC sources with controllable output level,
    frequency (for AC), and output enable/disable.
    """
    
    output_on: Parameter
    """Parameter to enable/disable source output."""
    
    level: Parameter
    """Parameter for output level (voltage or current)."""
    
    frequency: Optional[Parameter] = None
    """Parameter for AC frequency (None for DC sources)."""


class AbstractConverter(Instrument, ABC):
    """Abstract base class for signal converters (e.g., V→I).
    
    Provides interface for manual conversion parameters like transconductance,
    inversion, and optional phase/impedance characteristics.
    """
    
    gm_a_per_v: Parameter
    """Manual parameter for transconductance (A/V, RMS)."""
    
    invert: Parameter
    """Manual parameter for signal inversion (bool)."""
    
    phase_deg: Optional[Parameter] = None
    """Optional manual parameter for phase shift (degrees)."""
    
    primary_impedance_ohm: Optional[Parameter] = None
    """Optional manual parameter for primary impedance (Ω)."""


class AbstractAmplifier(Instrument, ABC):
    """Abstract base class for voltage amplifiers.
    
    Provides interface for manual amplifier parameters like gain,
    inversion, and optional coupling/bandwidth characteristics.
    """
    
    gain_v_per_v: Parameter
    """Manual parameter for voltage gain (V/V)."""
    
    invert: Parameter
    """Manual parameter for signal inversion (bool)."""
    
    coupling: Optional[Parameter] = None
    """Optional manual parameter for input coupling."""
    
    bandwidth_hz: Optional[Parameter] = None
    """Optional manual parameter for bandwidth (Hz)."""


class AbstractLockIn(Instrument, ABC):
    """Abstract base class for lock-in amplifiers.
    
    Provides interface for lock-in amplifier with demodulation frequency,
    time constant, sensitivity, input range, and readout parameters.
    """
    
    frequency: Parameter
    """Parameter for demodulation frequency (Hz)."""
    
    time_constant: Parameter
    """Parameter for time constant (s)."""
    
    sensitivity: Parameter
    """Parameter for input sensitivity/gain."""
    
    input_range: Parameter
    """Parameter for input voltage range (V)."""
    
    X: Parameter
    """Parameter for X component readout (V)."""
    
    Y: Parameter
    """Parameter for Y component readout (V)."""
    
    R: Parameter
    """Parameter for magnitude readout (V)."""
    
    Theta: Parameter
    """Parameter for phase readout (degrees)."""