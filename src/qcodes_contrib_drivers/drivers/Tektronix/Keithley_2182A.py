"""
QCoDeS driver for the Keithley 2182A nanovoltmeter.

This driver implements the full functionality based on the Keithley 2182A user manual,
with particular focus on the MEASure and FETCh commands and related functionality.
"""

from functools import partial
from typing import TYPE_CHECKING, Any
import time

from qcodes.instrument import VisaInstrument, VisaInstrumentKWArgs
from qcodes.validators import Bool, Enum, Ints, MultiType, Numbers

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing_extensions import Unpack
    from qcodes.parameters import Parameter


def _parse_output_string(s: str) -> str:
    """Parses and cleans string outputs of the Keithley"""
    # Remove surrounding whitespace and newline characters
    s = s.strip()

    # Remove surrounding quotes
    if (s[0] == s[-1]) and s.startswith(("'", '"')):
        s = s[1:-1]

    s = s.lower()

    # Convert some results to a better readable version
    conversions = {
        "mov": "moving",
        "rep": "repeat",
    }

    if s in conversions.keys():
        s = conversions[s]

    return s


def _parse_output_bool(value: str) -> bool:
    """Parse boolean output from the instrument"""
    return True if int(value) == 1 else False


class Keithley2182A(VisaInstrument):
    """
    QCoDeS driver for the Keithley 2182A nanovoltmeter.

    This driver provides comprehensive functionality for the Keithley 2182A,
    including voltage measurements, temperature readings, and various
    configuration options as specified in the user manual sections 12-15.

    The driver implements the MEASure and FETCh commands along with all
    related measurement and configuration functionality.
    """

    default_terminator = "\n"

    def __init__(
        self,
        name: str,
        address: str,
        reset: bool = False,
        **kwargs: "Unpack[VisaInstrumentKWArgs]",
    ):
        """
        Initialize the Keithley 2182A nanovoltmeter.

        Args:
            name: Name of the instrument
            address: VISA address of the instrument
            reset: Whether to reset the instrument upon initialization
            **kwargs: Additional arguments passed to VisaInstrument
        """
        super().__init__(name, address, **kwargs)

        self._trigger_sent = False

        # Mode mapping for measurement functions
        self._mode_map = {
            "dc voltage": '"VOLT:DC"',
            "temperature": '"TEMP"',
        }

        # Measurement mode parameter
        self.mode: Parameter = self.add_parameter(
            "mode",
            label="Measurement Mode",
            get_cmd="SENS:FUNC?",
            set_cmd="SENS:FUNC {}",
            val_mapping=self._mode_map,
            docstring="Set/get the measurement function (DC voltage or temperature)",
        )

        # Voltage measurement parameters
        self.voltage: Parameter = self.add_parameter(
            "voltage",
            label="DC Voltage",
            unit="V",
            get_cmd=self._measure_voltage,
            docstring="Measure DC voltage using the MEASure command",
        )

        # NPLC (Number of Power Line Cycles) parameter
        self.nplc: Parameter = self.add_parameter(
            "nplc",
            label="Integration Time (NPLC)",
            get_cmd=partial(self._get_mode_param, "NPLC", float),
            set_cmd=partial(self._set_mode_param, "NPLC"),
            vals=Numbers(min_value=0.01, max_value=10),
            docstring="Set/get the integration time in number of power line cycles",
        )

        # Voltage range parameter
        self.range: Parameter = self.add_parameter(
            "range",
            label="Measurement Range",
            unit="V",
            get_cmd=partial(self._get_mode_param, "RANG", float),
            set_cmd=partial(self._set_mode_param, "RANG"),
            vals=Numbers(min_value=1e-6, max_value=120),
            docstring="Set/get the measurement range",
        )

        # Auto range parameter
        self.auto_range_enabled: Parameter = self.add_parameter(
            "auto_range_enabled",
            label="Auto Range",
            get_cmd=partial(self._get_mode_param, "RANG:AUTO", lambda x: bool(int(x))),
            set_cmd=partial(self._set_mode_param, "RANG:AUTO", val_type=int),
            vals=Bool(),
            docstring="Enable/disable auto ranging",
        )

        # Line frequency parameter for NPLC calculations
        self.line_frequency: Parameter = self.add_parameter(
            "line_frequency",
            label="Line Frequency",
            unit="Hz",
            get_cmd="SYST:LFR?",
            set_cmd="SYST:LFR {}",
            get_parser=float,
            vals=Enum(50, 60),
            docstring="Set/get the power line frequency (50 or 60 Hz)",
        )

        # Measurement aperture time (alternative to NPLC)
        self.aperture_time: Parameter = self.add_parameter(
            "aperture_time",
            label="Aperture Time",
            unit="s",
            get_cmd=partial(self._get_mode_param, "APER", float),
            set_cmd=partial(self._set_mode_param, "APER"),
            vals=Numbers(min_value=0.0002, max_value=0.2),
            docstring="Set/get the measurement aperture time in seconds",
        )

        # Temperature measurement parameters
        self.temperature: Parameter = self.add_parameter(
            "temperature",
            label="Temperature",
            unit="K",
            get_cmd=self._measure_temperature,
            docstring="Measure temperature (requires appropriate probe)",
        )

        # Temperature units parameter
        self.temperature_units: Parameter = self.add_parameter(
            "temperature_units",
            label="Temperature Units",
            get_cmd="UNIT:TEMP?",
            set_cmd="UNIT:TEMP {}",
            val_mapping={"kelvin": "K", "celsius": "C", "fahrenheit": "F"},
            docstring="Set/get temperature measurement units",
        )

        # Averaging parameters
        self.averaging_enabled: Parameter = self.add_parameter(
            "averaging_enabled",
            label="Averaging Enabled",
            get_cmd="SENS:AVER?",
            set_cmd="SENS:AVER {}",
            val_mapping={True: "ON", False: "OFF"},
            docstring="Enable/disable measurement averaging",
        )

        self.averaging_count: Parameter = self.add_parameter(
            "averaging_count",
            label="Averaging Count",
            get_cmd="SENS:AVER:COUN?",
            set_cmd="SENS:AVER:COUN {}",
            get_parser=int,
            vals=Ints(min_value=1, max_value=100),
            docstring="Set/get the number of measurements to average",
        )

        # Trigger parameters
        self.trigger_source: Parameter = self.add_parameter(
            "trigger_source",
            label="Trigger Source",
            get_cmd="TRIG:SOUR?",
            set_cmd="TRIG:SOUR {}",
            val_mapping={
                "immediate": "IMM",
                "external": "EXT",
                "timer": "TIM",
                "manual": "MAN",
                "bus": "BUS",
            },
            docstring="Set/get the trigger source",
        )

        self.trigger_delay: Parameter = self.add_parameter(
            "trigger_delay",
            label="Trigger Delay",
            unit="s",
            get_cmd="TRIG:DEL?",
            set_cmd="TRIG:DEL {}",
            get_parser=float,
            vals=Numbers(min_value=0, max_value=999999.999),
            docstring="Set/get trigger delay in seconds",
        )

        # Display parameters
        self.display_enabled: Parameter = self.add_parameter(
            "display_enabled",
            label="Display Enabled",
            get_cmd="DISP:ENAB?",
            set_cmd="DISP:ENAB {}",
            val_mapping={True: "ON", False: "OFF"},
            docstring="Enable/disable the front panel display",
        )

        # Input impedance parameter (specific to nanovoltmeter)
        self.input_impedance: Parameter = self.add_parameter(
            "input_impedance",
            label="Input Impedance",
            get_cmd="SENS:VOLT:DC:IMP:AUTO?",
            set_cmd="SENS:VOLT:DC:IMP:AUTO {}",
            val_mapping={True: "ON", False: "OFF"},
            docstring="Enable/disable automatic input impedance selection",
        )

        # Analog filter for noise reduction
        self.analog_filter: Parameter = self.add_parameter(
            "analog_filter",
            label="Analog Filter",
            get_cmd="SENS:VOLT:DC:LPAS?",
            set_cmd="SENS:VOLT:DC:LPAS {}",
            val_mapping={True: "ON", False: "OFF"},
            docstring="Enable/disable analog low-pass filter for noise reduction",
        )

        # Digital filter for additional noise reduction
        self.digital_filter: Parameter = self.add_parameter(
            "digital_filter",
            label="Digital Filter",
            get_cmd="SENS:VOLT:DC:DFIL?",
            set_cmd="SENS:VOLT:DC:DFIL {}",
            val_mapping={True: "ON", False: "OFF"},
            docstring="Enable/disable digital filter for noise reduction",
        )

        # Initialize instrument settings
        if reset:
            self.reset()

        self.connect_message()

    def _get_mode_param(self, param: str, parser: "Callable[[str], Any]") -> Any:
        """
        Get a parameter value for the current measurement mode.

        Args:
            param: Parameter name to query
            parser: Function to parse the response

        Returns:
            Parsed parameter value
        """
        cmd = f"SENS:{param}?"
        response = self.ask(cmd)
        return parser(response)

    def _set_mode_param(self, param: str, value: Any, val_type: type = None) -> None:
        """
        Set a parameter value for the current measurement mode.

        Args:
            param: Parameter name to set
            value: Value to set
            val_type: Optional type conversion for boolean/integer values
        """
        if val_type is bool:
            value = "ON" if value else "OFF"
        elif val_type is int and isinstance(value, bool):
            # Convert boolean to integer for YAML compatibility
            value = 1 if value else 0
        elif val_type is int and not isinstance(value, int):
            # Ensure value is an integer
            value = int(value)
        cmd = f"SENS:{param} {value}"
        self.write(cmd)

    def _measure_voltage(self) -> float:
        """
        Measure DC voltage using the MEASure command.

        The MEASure command automatically configures the instrument
        for voltage measurement and returns the result.

        Returns:
            Measured voltage in volts
        """
        response = self.ask("MEAS:VOLT:DC?")
        return float(response)

    def _measure_temperature(self) -> float:
        """
        Measure temperature using the MEASure command.

        Returns:
            Measured temperature in the currently selected units
        """
        response = self.ask("MEAS:TEMP?")
        return float(response)

    def fetch(self) -> float:
        """
        Fetch the last measurement from the instrument buffer.

        The FETCh command retrieves the most recent measurement
        without triggering a new measurement.

        Returns:
            Last measured value
        """
        response = self.ask("FETC?")
        return float(response)

    def read(self) -> float:
        """
        Trigger and fetch a measurement.

        The READ command combines INIT and FETC operations.

        Returns:
            Measured value
        """
        response = self.ask("READ?")
        return float(response)

    def initiate_measurement(self) -> None:
        """
        Initiate a measurement.

        This command moves the instrument from the idle state
        to the wait-for-trigger state.
        """
        self.write("INIT")
        self._trigger_sent = True

    def abort_measurement(self) -> None:
        """
        Abort the current measurement and return to idle state.
        """
        self.write("ABOR")
        self._trigger_sent = False

    def trigger(self) -> None:
        """
        Send a software trigger to the instrument.
        """
        if not self._trigger_sent:
            self.initiate_measurement()
        self.write("*TRG")

    def auto_zero(self, enabled: bool = True) -> None:
        """
        Enable or disable auto-zero functionality.

        Args:
            enabled: True to enable auto-zero, False to disable
        """
        self.write(f"SENS:VOLT:DC:AZER {'ON' if enabled else 'OFF'}")

    def get_auto_zero(self) -> bool:
        """
        Get the current auto-zero setting.

        Returns:
            True if auto-zero is enabled, False otherwise
        """
        response = self.ask("SENS:VOLT:DC:AZER?")
        return _parse_output_bool(response)

    def configure_voltage_measurement(
        self,
        voltage_range: float = None,
        auto_range: bool = True,
        nplc: float = 1.0,
        auto_zero: bool = True,
    ) -> None:
        """
        Configure the instrument for voltage measurements.

        Args:
            voltage_range: Measurement range in volts (if auto_range is False)
            auto_range: Enable auto-ranging
            nplc: Integration time in power line cycles
            auto_zero: Enable auto-zero
        """
        # Set measurement function to DC voltage
        self.mode("dc voltage")

        # Configure ranging
        if auto_range:
            self.auto_range_enabled(True)
        else:
            self.auto_range_enabled(False)
            if voltage_range is not None:
                self.range(voltage_range)

        # Set integration time
        self.nplc(nplc)

        # Configure auto-zero
        self.auto_zero(auto_zero)

    def configure_temperature_measurement(
        self, units: str = "kelvin", nplc: float = 1.0
    ) -> None:
        """
        Configure the instrument for temperature measurements.

        Args:
            units: Temperature units ("kelvin", "celsius", or "fahrenheit")
            nplc: Integration time in power line cycles
        """
        # Set measurement function to temperature
        self.mode("temperature")

        # Set temperature units
        self.temperature_units(units)

        # Set integration time
        self.nplc(nplc)

    def get_measurement_status(self) -> dict:
        """
        Get comprehensive measurement status information.

        Returns:
            Dictionary containing measurement configuration and status
        """
        status = {}

        # Basic configuration
        status["mode"] = self.mode()
        status["range"] = self.range()
        status["auto_range"] = self.auto_range_enabled()
        status["nplc"] = self.nplc()

        # Averaging configuration
        status["averaging_enabled"] = self.averaging_enabled()
        if status["averaging_enabled"]:
            status["averaging_count"] = self.averaging_count()

        # Trigger configuration
        status["trigger_source"] = self.trigger_source()
        status["trigger_delay"] = self.trigger_delay()

        # Temperature specific settings (if applicable)
        if status["mode"] == "temperature":
            status["temperature_units"] = self.temperature_units()

        # Auto-zero setting (voltage mode)
        if status["mode"] == "dc voltage":
            status["auto_zero"] = self.get_auto_zero()

        return status

    def reset(self) -> None:
        """
        Reset the instrument to default settings.
        """
        self.write("*RST")
        # Wait for reset to complete
        time.sleep(1)
        self._trigger_sent = False

    def self_test(self) -> bool:
        """
        Perform instrument self-test.

        Returns:
            True if self-test passed, False otherwise
        """
        result = self.ask("*TST?")
        return int(result) == 0

    def get_error(self) -> tuple[int, str]:
        """
        Get the oldest error from the error queue.

        Returns:
            Tuple of (error_code, error_message)
        """
        response = self.ask("SYST:ERR?")
        parts = response.split(",", 1)
        error_code = int(parts[0])
        error_message = parts[1].strip().strip('"') if len(parts) > 1 else ""
        return error_code, error_message

    def clear_errors(self) -> None:
        """
        Clear all errors from the error queue.
        """
        self.write("*CLS")

    def set_measurement_speed(self, speed: str) -> None:
        """
        Set measurement speed preset (affects NPLC and filtering).

        Args:
            speed: Speed setting ("fast", "medium", "slow")
        """
        speed_settings = {
            "fast": {"nplc": 0.1, "analog_filter": False, "digital_filter": False},
            "medium": {"nplc": 1.0, "analog_filter": False, "digital_filter": False},
            "slow": {"nplc": 10.0, "analog_filter": True, "digital_filter": True},
        }

        if speed not in speed_settings:
            raise ValueError(
                f"Invalid speed setting. Choose from: {list(speed_settings.keys())}"
            )

        settings = speed_settings[speed]
        self.nplc(settings["nplc"])
        self.analog_filter(settings["analog_filter"])
        self.digital_filter(settings["digital_filter"])

    def measure_voltage_statistics(self, num_measurements: int = 10) -> dict:
        """
        Take multiple voltage measurements and return statistics.

        Args:
            num_measurements: Number of measurements to take

        Returns:
            Dictionary with mean, std, min, max values
        """
        import statistics

        measurements = []
        for _ in range(num_measurements):
            measurements.append(self._measure_voltage())

        return {
            "mean": statistics.mean(measurements),
            "stdev": statistics.stdev(measurements) if len(measurements) > 1 else 0,
            "min": min(measurements),
            "max": max(measurements),
            "count": len(measurements),
            "measurements": measurements,
        }

    def optimize_for_low_noise(self) -> None:
        """
        Configure the instrument for lowest noise measurements.

        This enables all noise reduction features and sets slow integration time.
        """
        self.set_measurement_speed("slow")
        self.auto_zero(True)
        self.averaging_enabled(True)
        self.averaging_count(10)
        self.input_impedance(True)  # Auto impedance selection

    def optimize_for_speed(self) -> None:
        """
        Configure the instrument for fastest measurements.

        This disables noise reduction features for maximum speed.
        """
        self.set_measurement_speed("fast")
        self.auto_zero(False)
        self.averaging_enabled(False)
        self.analog_filter(False)
        self.digital_filter(False)

    def check_ranges(self) -> dict:
        """
        Get available measurement ranges for the current mode.

        Returns:
            Dictionary with range information
        """
        mode = self.mode()

        if mode == "dc voltage":
            ranges = {
                "available_ranges": [0.1, 1.0, 10.0, 100.0],  # Volts
                "current_range": self.range(),
                "auto_range": self.auto_range_enabled(),
            }
        elif mode == "temperature":
            ranges = {
                "available_ranges": "Depends on probe type",
                "current_units": self.temperature_units(),
                "auto_range": "N/A for temperature",
            }
        else:
            ranges = {"error": "Unknown measurement mode"}

        return ranges
