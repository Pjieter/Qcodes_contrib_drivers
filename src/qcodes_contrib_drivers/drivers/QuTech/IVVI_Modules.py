"""
QCoDeS Instrument driver for manual Qutech IVVI rack modules.

This module provides software abstraction layers for manual IVVI rack modules
that do not require communication. These drivers serve as documentation and
parameter tracking tools for integration with measurement scripts.

Based on documentation at:
https://qtwork.tudelft.nl/~schouten/ivvi/index-ivvi.htm

Author: QCoDeS Community
"""

from abc import ABC, abstractmethod
from typing import Optional, Union
from qcodes.instrument import Instrument
from qcodes.parameters import Parameter
from qcodes.validators import Numbers, Enum


class IVVI_Module(Instrument, ABC):
    """
    Base class for manual IVVI rack modules.

    This class provides common functionality for manual IVVI modules that do
    not communicate electronically but need software representation for
    documentation, parameter tracking, and integration with measurement scripts.

    All IVVI modules inherit from this base class and implement their specific
    parameters and behaviors.
    """

    def __init__(self, name: str, **kwargs):
        """
        Initialize the IVVI module base class.

        Args:
            name: Name of the instrument instance
            **kwargs: Additional keyword arguments passed to parent Instrument
        """
        if self.__class__ is IVVI_Module:
            raise TypeError("IVVI_Module is an abstract base class and cannot be instantiated directly. "
                          "Use a specific module class like S4c, M2m, etc.")
                          
        super().__init__(name, **kwargs)

        # Common parameters for manual tracking
        self.add_parameter(
            "module_type",
            initial_value="Unknown",
            parameter_class=Parameter,
            vals=None,
            docstring="Type identifier for the IVVI module",
        )

        self.add_parameter(
            "rack_position",
            initial_value=None,
            parameter_class=Parameter,
            vals=None,
            docstring="Physical position of module in IVVI rack",
        )

        self.add_parameter(
            "notes",
            initial_value="",
            parameter_class=Parameter,
            vals=None,
            docstring="User notes about module configuration or usage",
        )

    def get_idn(self):
        """
        Get instrument identification.

        Returns:
            dict: Identification information
        """
        return {
            "vendor": "QuTech",
            "model": f"IVVI-{self.module_type()}",
            "serial": "Manual",
            "firmware": "N/A",
        }


class S4c(IVVI_Module):
    """
    Driver for the S4c Current/Voltage source module.

    This module is designed as a versatile source for V-I or I-V measurements.
    Based on the official IVVI S4c documentation.

    The S4c can operate in multiple modes:
    - [V] voltage source with current limit (1nA to 20mA range)
    - [V+R] voltage source with output resistance setting (1GΩ to 50Ω)
    - [I] current source with current range setting (1nA to 20mA/V)

    Features:
    - Buffered monitor outputs for source-measure-unit operation
    - Configurable output resistance via R-out switch
    - Single or symmetric output modes
    - Two control inputs: x1 and x0.01 for DC sweep and modulation
    - Overload protection with LED indicators
    """

    def __init__(self, name: str, **kwargs):
        """
        Initialize S4c current/voltage source module.

        Args:
            name: Name of the instrument instance
            **kwargs: Additional keyword arguments
        """
        super().__init__(name, **kwargs)

        # Set module type
        self.module_type("S4c")

        # Source mode configuration
        self.add_parameter(
            "source_mode",
            initial_value="V",
            vals=Enum("V", "V+R", "I"),
            docstring="Source operating mode: V (voltage), V+R (voltage+resistance), I (current)",
            parameter_class=Parameter,
        )

        # Range settings (affects current limit, output resistance, or current range)
        self.add_parameter(
            "range_setting",
            initial_value="1uA",
            vals=Enum("1nA", "10nA", "100nA", "1uA", "10uA", "100uA", "1mA", "10mA", "20mA"),
            docstring="Range setting - interpretation depends on source mode",
            parameter_class=Parameter,
        )

        # Output resistance setting
        self.add_parameter(
            "output_resistance_mode",
            initial_value="R/1000",
            vals=Enum("R/1000", "R/10"),
            docstring="Output resistance mode: R/1000 (highest accuracy), R/10 (lowest noise)",
            parameter_class=Parameter,
        )

        # Output mode configuration
        self.add_parameter(
            "output_mode",
            initial_value="single",
            vals=Enum("single", "symmetric"),
            docstring="Output mode: single (pin 4 out, pin 2 ground) or symmetric (pin 4 out, pin 2 -out)",
            parameter_class=Parameter,
        )

        # Control input configuration
        self.add_parameter(
            "x1_input_enabled",
            initial_value=True,
            vals=Enum(True, False),
            docstring="X1 control input enabled (default enabled)",
            parameter_class=Parameter,
        )

        self.add_parameter(
            "x0_01_input_enabled",
            initial_value=False,
            vals=Enum(True, False),
            docstring="X0.01 control input enabled (requires jumper setting)",
            parameter_class=Parameter,
        )

        # Output voltage and current (for monitoring/documentation)
        self.add_parameter(
            "output_voltage",
            initial_value=0.0,
            unit="V",
            vals=Numbers(-8.0, 8.0),  # Max ±8V in symmetric mode
            docstring="Output voltage (manually read from V-out LED or measured)",
            parameter_class=Parameter,
        )

        self.add_parameter(
            "output_current",
            initial_value=0.0,
            unit="A",
            vals=Numbers(-20e-3, 20e-3),  # Max ±20mA
            docstring="Output current (manually set or measured)",
            parameter_class=Parameter,
        )

        # Monitor outputs for SMU operation
        self.add_parameter(
            "voltage_monitor",
            initial_value=0.0,
            unit="V",
            vals=Numbers(-10.0, 10.0),
            docstring="Voltage monitor output (>10kHz bandwidth)",
            parameter_class=Parameter,
        )

        self.add_parameter(
            "current_monitor",
            initial_value=0.0,
            unit="A",
            vals=Numbers(-20e-3, 20e-3),
            docstring="Current monitor output (>10kHz bandwidth)",
            parameter_class=Parameter,
        )

        # Status indicators
        self.add_parameter(
            "clip_indicator",
            initial_value=False,
            vals=Enum(True, False),
            docstring="Overload LED status (voltage exceeds 2-4V)",
            parameter_class=Parameter,
        )

        self.add_parameter(
            "v_unbal_indicator",
            initial_value=False,
            vals=Enum(True, False),
            docstring="Voltage unbalance LED status (symmetric mode only)",
            parameter_class=Parameter,
        )

        # Control input values
        self.add_parameter(
            "x1_input_voltage",
            initial_value=0.0,
            unit="V",
            vals=Numbers(-10.0, 10.0),
            docstring="X1 control input voltage (from DAC for DC sweep)",
            parameter_class=Parameter,
        )

        self.add_parameter(
            "x0_01_input_voltage",
            initial_value=0.0,
            unit="V",
            vals=Numbers(-10.0, 10.0),
            docstring="X0.01 control input voltage (for modulation via iso-amp)",
            parameter_class=Parameter,
        )

        # Configuration helper parameters
        self.add_parameter(
            "maximum_output_voltage",
            get_cmd=self._get_max_output_voltage,
            unit="V",
            docstring="Maximum output voltage based on current configuration",
        )

        self.add_parameter(
            "current_limit",
            get_cmd=self._get_current_limit,
            unit="A",
            docstring="Current limit based on source mode and range setting",
        )

    def _get_max_output_voltage(self) -> float:
        """Get maximum output voltage based on configuration."""
        if self.output_mode() == "symmetric":
            return 8.0  # ±4V to ±8V in symmetric mode
        else:
            return 4.0  # Typical single-ended maximum

    def _get_current_limit(self) -> float:
        """Get current limit based on source mode and range setting."""
        range_str = self.range_setting()
        
        # Parse range setting to get numeric value
        if "nA" in range_str:
            multiplier = 1e-9
        elif "uA" in range_str:
            multiplier = 1e-6
        elif "mA" in range_str:
            multiplier = 1e-3
        else:
            multiplier = 1.0
            
        value = float(range_str.replace("nA", "").replace("uA", "").replace("mA", ""))
        
        if self.source_mode() == "V":
            # In voltage mode, range sets current limit (approx 3x range)
            return 3.0 * value * multiplier
        else:
            # In current mode, range is the current range
            return value * multiplier

    def get_status_summary(self) -> dict:
        """Get a summary of the current S4c configuration and status."""
        return {
            "source_mode": self.source_mode(),
            "range_setting": self.range_setting(),
            "output_mode": self.output_mode(),
            "output_voltage": self.output_voltage(),
            "output_current": self.output_current(),
            "max_output_voltage": self.maximum_output_voltage(),
            "current_limit": self.current_limit(),
            "clip_indicator": self.clip_indicator(),
            "v_unbal_indicator": self.v_unbal_indicator(),
            "x1_enabled": self.x1_input_enabled(),
            "x0_01_enabled": self.x0_01_input_enabled(),
        }


class M2m(IVVI_Module):
    """
    Driver for the M2m voltage source module.

    The M2m is a 2-channel voltage source module for the IVVI rack.
    Based on the official IVVI documentation.

    Specifications:
    - 2 independent voltage source channels
    - Range: ±4V with 16-bit resolution (0-65535 steps)
    - Output current: max 10 mA per channel
    - Temperature coefficient: <50 ppm/K
    - Manual control via front panel
    - Protection: short circuit and overload
    """

    def __init__(self, name: str, **kwargs):
        """
        Initialize M2m voltage source module.

        Args:
            name: Name of the instrument instance
            **kwargs: Additional keyword arguments
        """
        super().__init__(name, **kwargs)

        # Set module type
        self.module_type("M2m")

        # Voltage range and resolution based on M2m specifications
        self._max_voltage = 4.0  # ±4V
        self._resolution_bits = 16  # 0-65535 steps
        self._voltage_resolution = (2 * self._max_voltage) / (2**self._resolution_bits)
        self._max_current = 10e-3  # 10 mA max output current

        # Add channel parameters
        for i in range(1, 3):  # 2 channels
            self.add_parameter(
                f"ch{i}_voltage",
                initial_value=0.0,
                unit="V",
                vals=Numbers(-self._max_voltage, self._max_voltage),
                docstring=f"Channel {i} voltage setting (manually set on device)",
                parameter_class=Parameter,
            )

            self.add_parameter(
                f"ch{i}_enabled",
                initial_value=False,
                vals=Enum(True, False),
                docstring=f"Channel {i} output enable state",
                parameter_class=Parameter,
            )

        # Module-specific parameters
        self.add_parameter(
            "voltage_range",
            initial_value="±4V",
            vals=Enum("±4V"),
            docstring="Voltage output range setting",
            parameter_class=Parameter,
        )

        self.add_parameter(
            "max_current",
            get_cmd=lambda: self._max_current,
            unit="A",
            docstring="Maximum output current per channel",
        )

        self.add_parameter(
            "resolution",
            get_cmd=lambda: self._voltage_resolution,
            unit="V",
            docstring="Voltage resolution based on range and DAC bits",
        )


class M2b(IVVI_Module):
    """
    Driver for the M2b voltage source module.

    The M2b is a 2-channel voltage source module for the IVVI rack.
    Based on the official IVVI documentation.

    Specifications:
    - 2 independent voltage source channels
    - Range: ±10V with 16-bit resolution (0-65535 steps)
    - Output current: max 2 mA per channel
    - High precision and low noise
    - Manual control via front panel
    - Protection: short circuit and overload
    """

    def __init__(self, name: str, **kwargs):
        """
        Initialize M2b voltage source module.

        Args:
            name: Name of the instrument instance
            **kwargs: Additional keyword arguments
        """
        super().__init__(name, **kwargs)

        # Set module type
        self.module_type("M2b")

        # Voltage range and resolution based on M2b specifications
        self._max_voltage = 10.0  # ±10V
        self._resolution_bits = 16  # 0-65535 steps
        self._voltage_resolution = (2 * self._max_voltage) / (2**self._resolution_bits)
        self._max_current = 2e-3  # 2 mA max output current

        # Add channel parameters
        for i in range(1, 3):  # 2 channels
            self.add_parameter(
                f"ch{i}_voltage",
                initial_value=0.0,
                unit="V",
                vals=Numbers(-self._max_voltage, self._max_voltage),
                docstring=f"Channel {i} voltage setting (manually set on device)",
                parameter_class=Parameter,
            )

            self.add_parameter(
                f"ch{i}_enabled",
                initial_value=False,
                vals=Enum(True, False),
                docstring=f"Channel {i} output enable state",
                parameter_class=Parameter,
            )

        # Module-specific parameters
        self.add_parameter(
            "voltage_range",
            initial_value="±10V",
            vals=Enum("±10V"),
            docstring="Voltage output range setting",
            parameter_class=Parameter,
        )

        self.add_parameter(
            "max_current",
            get_cmd=lambda: self._max_current,
            unit="A",
            docstring="Maximum output current per channel",
        )

        self.add_parameter(
            "resolution",
            get_cmd=lambda: self._voltage_resolution,
            unit="V",
            docstring="Voltage resolution based on range and DAC bits",
        )


class M1b(IVVI_Module):
    """
    Driver for the M1b voltage source module.

    The M1b is a 1-channel voltage source module for the IVVI rack.
    Based on the official IVVI documentation.

    Specifications:
    - 1 voltage source channel
    - Range: ±10V with 16-bit resolution (0-65535 steps)
    - Output current: max 2 mA
    - High precision and stability
    - Manual control via front panel
    - Protection: short circuit and overload
    """

    def __init__(self, name: str, **kwargs):
        """
        Initialize M1b voltage source module.

        Args:
            name: Name of the instrument instance
            **kwargs: Additional keyword arguments
        """
        super().__init__(name, **kwargs)

        # Set module type
        self.module_type("M1b")

        # Voltage range and resolution based on M1b specifications
        self._max_voltage = 10.0  # ±10V
        self._resolution_bits = 16  # 0-65535 steps
        self._voltage_resolution = (2 * self._max_voltage) / (2**self._resolution_bits)
        self._max_current = 2e-3  # 2 mA max output current

        # Add channel parameter (single channel)
        self.add_parameter(
            "ch1_voltage",
            initial_value=0.0,
            unit="V",
            vals=Numbers(-self._max_voltage, self._max_voltage),
            docstring="Channel 1 voltage setting (manually set on device)",
            parameter_class=Parameter,
        )

        self.add_parameter(
            "ch1_enabled",
            initial_value=False,
            vals=Enum(True, False),
            docstring="Channel 1 output enable state",
            parameter_class=Parameter,
        )

        # Module-specific parameters
        self.add_parameter(
            "voltage_range",
            initial_value="±10V",
            vals=Enum("±10V"),
            docstring="Voltage output range setting",
            parameter_class=Parameter,
        )

        self.add_parameter(
            "max_current",
            get_cmd=lambda: self._max_current,
            unit="A",
            docstring="Maximum output current",
        )

        self.add_parameter(
            "resolution",
            get_cmd=lambda: self._voltage_resolution,
            unit="V",
            docstring="Voltage resolution based on range and DAC bits",
        )


class VId(IVVI_Module):
    """
    Driver for the VId voltage measurement module.

    The VId is a voltage measurement module for the IVVI rack.
    Based on the official IVVI documentation including M1h, S3b and isolation amplifier docs.

    Specifications:
    - 8 voltage measurement channels
    - Range: ±10V with 16-bit resolution
    - Input impedance: >10^12 Ω
    - Bandwidth: DC to 1 kHz
    - Accuracy: ±0.1% of reading ±1 digit
    - Common mode rejection: >80 dB
    - Isolation: 1000V
    - Manual readout via front panel display
    """

    def __init__(self, name: str, num_channels: int = 8, **kwargs):
        """
        Initialize VId voltage measurement module.

        Args:
            name: Name of the instrument instance
            num_channels: Number of measurement channels (default 8)
            **kwargs: Additional keyword arguments
        """
        super().__init__(name, **kwargs)

        # Set module type
        self.module_type("VId")

        # Measurement specifications based on VId documentation
        self._max_voltage = 10.0  # ±10V measurement range
        self._resolution_bits = 16  # 16-bit resolution
        self._voltage_resolution = (2 * self._max_voltage) / (2**self._resolution_bits)
        self._num_channels = num_channels
        self._input_impedance = 1e12  # >10^12 Ω
        self._bandwidth = 1000  # 1 kHz
        self._accuracy = 0.001  # ±0.1%

        # Add channel parameters
        for i in range(1, num_channels + 1):
            self.add_parameter(
                f"ch{i}_voltage",
                initial_value=0.0,
                unit="V",
                vals=Numbers(-self._max_voltage, self._max_voltage),
                docstring=f"Channel {i} measured voltage (manually read from device)",
                parameter_class=Parameter,
            )

            self.add_parameter(
                f"ch{i}_enabled",
                initial_value=True,
                vals=Enum(True, False),
                docstring=f"Channel {i} measurement enable state",
                parameter_class=Parameter,
            )

        # Module-specific parameters
        self.add_parameter(
            "measurement_range",
            initial_value="±10V",
            vals=Enum("±10V"),
            docstring="Voltage measurement range setting",
            parameter_class=Parameter,
        )

        self.add_parameter(
            "input_impedance",
            get_cmd=lambda: self._input_impedance,
            unit="Ω",
            docstring="Input impedance of measurement channels",
        )

        self.add_parameter(
            "bandwidth",
            get_cmd=lambda: self._bandwidth,
            unit="Hz",
            docstring="Measurement bandwidth",
        )

        self.add_parameter(
            "accuracy",
            get_cmd=lambda: self._accuracy,
            docstring="Measurement accuracy as fraction of reading",
        )

        self.add_parameter(
            "resolution",
            get_cmd=lambda: self._voltage_resolution,
            unit="V",
            docstring="Voltage measurement resolution",
        )

        self.add_parameter(
            "num_channels",
            get_cmd=lambda: self._num_channels,
            docstring="Number of measurement channels available",
        )


class IVd(IVVI_Module):
    """
    Driver for the IVd combined source-measure module.

    The IVd is a combined source and measurement module for the IVVI rack.
    Based on the official IVVI documentation including isolation amplifier specs.

    Specifications:
    - 4 independent source-measure channels
    - Voltage source range: ±4V with 16-bit resolution
    - Current measurement range: ±1 μA with high sensitivity
    - Source accuracy: ±0.1% of setting
    - Measurement accuracy: ±0.1% of reading
    - Isolation: 1000V between channels
    - Protection: overcurrent and overvoltage
    - Manual control and readout via front panel
    """

    def __init__(self, name: str, num_channels: int = 4, **kwargs):
        """
        Initialize IVd source-measure module.

        Args:
            name: Name of the instrument instance
            num_channels: Number of source-measure channels (default 4)
            **kwargs: Additional keyword arguments
        """
        super().__init__(name, **kwargs)

        # Set module type
        self.module_type("IVd")

        # Source and measurement specifications based on IVd documentation
        self._max_voltage = 4.0  # ±4V source range
        self._max_current = 1e-6  # ±1 μA measurement range
        self._resolution_bits = 16  # 16-bit resolution
        self._voltage_resolution = (2 * self._max_voltage) / (2**self._resolution_bits)
        self._current_resolution = (2 * self._max_current) / (2**self._resolution_bits)
        self._num_channels = num_channels
        self._source_accuracy = 0.001  # ±0.1%
        self._measure_accuracy = 0.001  # ±0.1%

        # Add channel parameters
        for i in range(1, num_channels + 1):
            # Source parameters
            self.add_parameter(
                f"ch{i}_voltage",
                initial_value=0.0,
                unit="V",
                vals=Numbers(-self._max_voltage, self._max_voltage),
                docstring=f"Channel {i} voltage source setting (manually set on device)",
                parameter_class=Parameter,
            )

            self.add_parameter(
                f"ch{i}_source_enabled",
                initial_value=False,
                vals=Enum(True, False),
                docstring=f"Channel {i} voltage source enable state",
                parameter_class=Parameter,
            )

            # Measurement parameters
            self.add_parameter(
                f"ch{i}_current",
                initial_value=0.0,
                unit="A",
                vals=Numbers(-self._max_current, self._max_current),
                docstring=f"Channel {i} measured current (manually read from device)",
                parameter_class=Parameter,
            )

            self.add_parameter(
                f"ch{i}_measure_enabled",
                initial_value=True,
                vals=Enum(True, False),
                docstring=f"Channel {i} current measurement enable state",
                parameter_class=Parameter,
            )

        # Module-specific parameters
        self.add_parameter(
            "voltage_range",
            initial_value="±4V",
            vals=Enum("±4V"),
            docstring="Voltage source range setting",
            parameter_class=Parameter,
        )

        self.add_parameter(
            "current_range",
            initial_value="±1uA",
            vals=Enum("±1uA"),
            docstring="Current measurement range setting",
            parameter_class=Parameter,
        )

        self.add_parameter(
            "source_accuracy",
            get_cmd=lambda: self._source_accuracy,
            docstring="Voltage source accuracy as fraction of setting",
        )

        self.add_parameter(
            "measure_accuracy",
            get_cmd=lambda: self._measure_accuracy,
            docstring="Current measurement accuracy as fraction of reading",
        )

        self.add_parameter(
            "voltage_resolution",
            get_cmd=lambda: self._voltage_resolution,
            unit="V",
            docstring="Voltage source resolution",
        )

        self.add_parameter(
            "current_resolution",
            get_cmd=lambda: self._current_resolution,
            unit="A",
            docstring="Current measurement resolution",
        )

        self.add_parameter(
            "num_channels",
            get_cmd=lambda: self._num_channels,
            docstring="Number of source-measure channels available",
        )
