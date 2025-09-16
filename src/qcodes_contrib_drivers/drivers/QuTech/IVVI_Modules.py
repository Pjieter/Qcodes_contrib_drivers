"""
QCoDeS Instrument driver for manual Qutech IVVI rack modules.

This module provides software abstraction layers for manual IVVI rack modules
that do not require communication. These drivers serve as documentation and
parameter tracking tools for integration with measurement scripts.

Based on documentation at:
https://qtwork.tudelft.nl/~schouten/ivvi/index-ivvi.htm

Author: QCoDeS Community
"""

from typing import Optional, Union
from qcodes.instrument import Instrument
from qcodes.parameters import Parameter
from qcodes.validators import Numbers, Enum


class IVVI_Module(Instrument):
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
    Driver for the S4c current source module.

    The S4c is a 4-channel current source module for the IVVI rack.
    This driver provides software representation for manual operation.

    Specifications (typical):
    - 4 independent current source channels
    - Range: ±10 μA with 16-bit resolution
    - Manual control via front panel
    """

    def __init__(self, name: str, **kwargs):
        """
        Initialize S4c current source module.

        Args:
            name: Name of the instrument instance
            **kwargs: Additional keyword arguments
        """
        super().__init__(name, **kwargs)

        # Set module type
        self.module_type("S4c")

        # Current range and resolution
        self._max_current = 10e-6  # 10 μA
        self._resolution_bits = 16
        self._current_resolution = (2 * self._max_current) / (2**self._resolution_bits)

        # Add channel parameters
        for i in range(1, 5):  # 4 channels
            self.add_parameter(
                f"ch{i}_current",
                initial_value=0.0,
                unit="A",
                vals=Numbers(-self._max_current, self._max_current),
                docstring=f"Channel {i} current setting (manually set on device)",
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
            "current_range",
            initial_value="10uA",
            vals=Enum("10uA"),
            docstring="Current output range setting",
            parameter_class=Parameter,
        )

        self.add_parameter(
            "resolution",
            get_cmd=lambda: self._current_resolution,
            unit="A",
            docstring="Current resolution based on range and DAC bits",
        )


class M2m(IVVI_Module):
    """
    Driver for the M2m voltage source module.

    The M2m is a 2-channel voltage source module for the IVVI rack.
    This driver provides software representation for manual operation.

    Specifications (typical):
    - 2 independent voltage source channels
    - Range: ±4V with 16-bit resolution
    - Manual control via front panel
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

        # Voltage range and resolution
        self._max_voltage = 4.0  # ±4V
        self._resolution_bits = 16
        self._voltage_resolution = (2 * self._max_voltage) / (2**self._resolution_bits)

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
            "resolution",
            get_cmd=lambda: self._voltage_resolution,
            unit="V",
            docstring="Voltage resolution based on range and DAC bits",
        )


class M2b(IVVI_Module):
    """
    Driver for the M2b voltage source module.

    The M2b is a 2-channel voltage source module (similar to M2m) for the IVVI rack.
    This driver provides software representation for manual operation.

    Specifications (typical):
    - 2 independent voltage source channels
    - Range: ±4V with 16-bit resolution
    - Manual control via front panel
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

        # Voltage range and resolution (same as M2m)
        self._max_voltage = 4.0  # ±4V
        self._resolution_bits = 16
        self._voltage_resolution = (2 * self._max_voltage) / (2**self._resolution_bits)

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
            "resolution",
            get_cmd=lambda: self._voltage_resolution,
            unit="V",
            docstring="Voltage resolution based on range and DAC bits",
        )


class M1b(IVVI_Module):
    """
    Driver for the M1b voltage source module.

    The M1b is a 1-channel voltage source module for the IVVI rack.
    This driver provides software representation for manual operation.

    Specifications (typical):
    - 1 voltage source channel
    - Range: ±4V with 16-bit resolution
    - Manual control via front panel
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

        # Voltage range and resolution
        self._max_voltage = 4.0  # ±4V
        self._resolution_bits = 16
        self._voltage_resolution = (2 * self._max_voltage) / (2**self._resolution_bits)

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
            initial_value="±4V",
            vals=Enum("±4V"),
            docstring="Voltage output range setting",
            parameter_class=Parameter,
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
    This driver provides software representation for manual operation.

    Specifications (typical):
    - Multiple voltage measurement channels
    - High input impedance
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

        # Measurement specifications
        self._max_voltage = 10.0  # ±10V typical measurement range
        self._resolution_bits = 16
        self._voltage_resolution = (2 * self._max_voltage) / (2**self._resolution_bits)
        self._num_channels = num_channels

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
    This driver provides software representation for manual operation.

    Specifications (typical):
    - Combined voltage source and current measurement
    - Voltage source range: ±4V with 16-bit resolution
    - Current measurement with high sensitivity
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

        # Source and measurement specifications
        self._max_voltage = 4.0  # ±4V source range
        self._max_current = 100e-6  # ±100 μA measurement range (typical)
        self._resolution_bits = 16
        self._voltage_resolution = (2 * self._max_voltage) / (2**self._resolution_bits)
        self._current_resolution = (2 * self._max_current) / (2**self._resolution_bits)
        self._num_channels = num_channels

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
            initial_value="±100uA",
            vals=Enum("±100uA"),
            docstring="Current measurement range setting",
            parameter_class=Parameter,
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
