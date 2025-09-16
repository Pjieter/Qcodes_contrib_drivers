# QuTech IVVI Manual Modules

This module provides QCoDeS instrument drivers for manual IVVI rack modules. These drivers serve as software abstraction layers for documentation, parameter tracking, and integration with measurement scripts for modules that are operated manually.

## Overview

The IVVI manual modules complement the existing RS232-based IVVI driver by providing software representations of manual modules. They are designed for:

- **Documentation**: Keep track of module configurations and settings
- **Parameter tracking**: Monitor and validate parameter ranges  
- **Integration**: Seamless integration with QCoDeS measurement scripts
- **Extensibility**: Easy to add new module types

## Available Modules

### Base Class: `IVVI_Module`

All manual modules inherit from this base class which provides:
- Common parameters: `module_type`, `rack_position`, `notes`
- Standard `get_idn()` method
- Consistent interface across all modules

### Current Source Modules

#### `S4c` - 4-Channel Current Source
- **Range**: ±10 μA with 16-bit resolution
- **Channels**: 4 independent current outputs
- **Parameters**: 
  - `ch1_current` through `ch4_current` (range: ±10 μA)
  - `ch1_enabled` through `ch4_enabled` (boolean)
  - `current_range`, `resolution`

### Voltage Source Modules

#### `M2m` - 2-Channel Voltage Source  
- **Range**: ±4V with 16-bit resolution
- **Channels**: 2 independent voltage outputs
- **Parameters**:
  - `ch1_voltage`, `ch2_voltage` (range: ±4V)
  - `ch1_enabled`, `ch2_enabled` (boolean)
  - `voltage_range`, `resolution`

#### `M2b` - 2-Channel Voltage Source
- Similar to M2m with same specifications and parameters

#### `M1b` - 1-Channel Voltage Source
- **Range**: ±4V with 16-bit resolution  
- **Channels**: 1 voltage output
- **Parameters**:
  - `ch1_voltage` (range: ±4V)
  - `ch1_enabled` (boolean)
  - `voltage_range`, `resolution`

### Measurement Modules

#### `VId` - Multi-Channel Voltage Measurement
- **Range**: ±10V measurement range
- **Channels**: Configurable (default 8 channels)
- **Parameters**:
  - `ch1_voltage` through `chN_voltage` (range: ±10V)
  - `ch1_enabled` through `chN_enabled` (boolean, default True)
  - `measurement_range`, `resolution`, `num_channels`

### Source-Measure Modules

#### `IVd` - Multi-Channel Source-Measure
- **Voltage source**: ±4V with 16-bit resolution
- **Current measurement**: ±100 μA with 16-bit resolution
- **Channels**: Configurable (default 4 channels)
- **Parameters**:
  - `ch1_voltage` through `chN_voltage` (range: ±4V)
  - `ch1_current` through `chN_current` (range: ±100 μA)
  - `ch1_source_enabled` through `chN_source_enabled` (boolean)
  - `ch1_measure_enabled` through `chN_measure_enabled` (boolean, default True)
  - `voltage_range`, `current_range`, `voltage_resolution`, `current_resolution`, `num_channels`

## Usage Examples

### Basic Setup

```python
from qcodes_contrib_drivers.drivers.QuTech.IVVI_manual import S4c, M2m, VId, IVd

# Create current source
current_source = S4c('cs1')
current_source.rack_position('Slot 1')
current_source.notes('Gate voltage control')

# Create voltage source  
voltage_source = M2m('vs1')
voltage_source.rack_position('Slot 2')

# Create voltmeter with 4 channels
voltmeter = VId('vm1', num_channels=4)
voltmeter.rack_position('Slot 3')

# Create source-measure unit with 2 channels
smu = IVd('smu1', num_channels=2)
smu.rack_position('Slot 4')
```

### Setting Parameters

```python
# Configure current source
current_source.ch1_enabled(True)
current_source.ch1_current(1e-6)  # 1 μA

# Configure voltage source
voltage_source.ch1_enabled(True)
voltage_source.ch1_voltage(0.5)   # 0.5 V

# Configure source-measure
smu.ch1_source_enabled(True)
smu.ch1_voltage(2.0)              # 2.0 V source
smu.ch1_current(50e-6)            # 50 μA measured
```

### Parameter Validation

```python
# Parameters are automatically validated
try:
    current_source.ch1_current(15e-6)  # Fails: exceeds ±10 μA range
except ValueError as e:
    print(f"Invalid value: {e}")

# Check ranges and resolution
print(f"Current range: {current_source.current_range()}")
print(f"Resolution: {current_source.resolution():.2e} A")
```

### Integration with Measurement Scripts

```python
# Use in measurement loops
for voltage in np.linspace(-1, 1, 21):
    # Set voltage (manually on device)
    voltage_source.ch1_voltage(voltage)
    
    # Record measurement (manually read from device)
    measured_current = 45e-6  # Read from device
    smu.ch1_current(measured_current)
    
    # Log the snapshot for documentation
    snapshot = {
        'voltage_set': voltage_source.ch1_voltage(),
        'current_measured': smu.ch1_current(),
        'timestamp': time.time()
    }
```

### Module Information

```python
# Get module information
for module in [current_source, voltage_source, voltmeter, smu]:
    idn = module.get_idn()
    print(f"{module.name}: {idn['vendor']} {idn['model']}")
    print(f"  Position: {module.rack_position()}")
    print(f"  Type: {module.module_type()}")
```

## Extending the Framework

Adding new IVVI modules is straightforward:

```python
class NewModule(IVVI_Module):
    """Driver for a new IVVI module."""
    
    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)
        
        # Set module type
        self.module_type('NewModule')
        
        # Add module-specific parameters
        self.add_parameter(
            'some_parameter',
            initial_value=0.0,
            unit='V',
            vals=Numbers(-10, 10),
            docstring='Description of parameter',
            parameter_class=Parameter
        )
```

## Design Philosophy

These manual modules are designed with the following principles:

1. **Non-invasive**: They complement rather than replace existing drivers
2. **Consistent**: All modules follow the same parameter naming and structure
3. **Extensible**: Easy to add new modules following the established pattern
4. **Documentation-focused**: Serve primarily as software documentation tools
5. **QCoDeS-compliant**: Follow QCoDeS conventions for instrument drivers

## Notes

- These are **manual instruments** - they do not communicate electronically
- Parameter values must be manually set on the physical devices  
- The software parameters serve as documentation and validation tools
- Ranges and resolutions are based on typical IVVI module specifications
- For electronic control, use the existing IVVI RS232 driver instead