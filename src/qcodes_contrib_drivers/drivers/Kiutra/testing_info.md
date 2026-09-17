The tests should will be described down below for each channel seperatly with specific api calls for testing. To connect to a specific device, you need to call Device(name_of_device, ip_adress, port) with Device being the specific device type (e.g. TemperatureControl, ADRControl, MagnetControl etc.)

The ip adress of this system is 192.168.11.20

# TemperatureChannel

The temperature that can be set for the kiutra is between 0.083 and 300 K. The lower limit is because that's the limit of the thermometer calibration.
There are four modes of temperature control, universal, cadr, adr, and heater. All modes have a maximum ramp rate of 2K/min. The adr modes have seperate ramp limits that depend on the temperature. You can get the ramp limits by calling ADRControl.query_value("ramp_limits") where the list of tuples is ordered like [(min_temp, max_temp, max_ramp), ...].
Depending on the control mode selected, the ramp should be validated when setting a temperature.
After calling the start_control method, the test should check if the actual control method has started on the instrument. That can be done by calling TemperatureControl.query_value('status'), this gives a list [int, string]. Status 200 is '', or stable or done, status 210 is initializing, status 220 is up/down (control_mode).
After each test, the temperaturecontrol needs to be stopped. That can be done my calling the method stop.

# MagnetChannel
The maximum field that can be set is +/- 5.5 Tesla. The maximum ramp rate is 0.5T