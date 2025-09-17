# IVVI Rack Signal Chain

This module provides a modular signal chain architecture for the IVVI rack topology:

```
[MFLI AC Voltage Source] → [Manual V→I Transformer] → [Sample] → [Manual Voltage Preamp] → [MFLI Input & Demod]
```

## Key Features

- **Single Current Setpoint**: `I_set` parameter automatically calculates required source voltage
- **Frequency Coupling**: `reference_frequency` synchronizes source and demod frequencies  
- **Guard Functions**: Automatic warnings for potential input overloads
- **Derived Parameters**: Physics-relevant readouts (V_sample, I_meas, etc.)
- **Modular Design**: Abstract bases + concrete implementations for extensibility

## Quick Start

```python
from qcodes_contrib_drivers.drivers.ZurichInstruments.MFLI import MFLI
from qcodes_contrib_drivers.drivers.virtual import (
    MFLISource, ManualVITransformer, ManualVoltagePreamp, 
    MFLILockIn, SignalChain
)

# Connect to MFLI hardware
mfli_hw = MFLI('mfli', 'dev1234', demod=0, sigout=0, 
               auxouts={'X': 0, 'Y': 1, 'R': 2, 'Theta': 3})

# Create signal chain nodes
src_v = MFLISource('source', mfli_hw)
vi_transformer = ManualVITransformer('vi')
preamp = ManualVoltagePreamp('preamp')
lockin = MFLILockIn('lockin', mfli_hw)

# Configure manual parameters
vi_transformer.gm_a_per_v.set(1e-3)    # 1 mA/V transconductance
preamp.gain_v_per_v.set(100.0)         # 100 V/V gain

# Create unified interface
ivvi_rack = SignalChain(src_v, vi_transformer, preamp, lockin)

# Set sample resistance estimate for guards and current measurement
ivvi_rack.R_est.set(10e3)  # 10 kΩ

# Set target current - automatically calculates source voltage
ivvi_rack.I_set.set(1e-6)  # 1 µA
# → Sets excitation_v_ac = 1e-6 / 1e-3 = 1e-3 V
# → Turns output_on = True

# Coupled frequency control
ivvi_rack.reference_frequency.set(1500)  # Sets both source and demod

# Read derived parameters
print(f"Commanded current: {ivvi_rack.I_cmd()} A")
print(f"Measured sample voltage: {ivvi_rack.V_sample_ac_meas()} V")
print(f"Measured current: {ivvi_rack.I_meas()} A")
```

## Architecture

### Abstract Base Classes (`signal_chain_abstracts.py`)

- `AbstractSource`: Voltage/current sources with `output_on`, `level`, `frequency`
- `AbstractConverter`: V→I converters with manual `gm_a_per_v`, `invert` 
- `AbstractAmplifier`: V→V amplifiers with manual `gain_v_per_v`, `invert`
- `AbstractLockIn`: Lock-ins with `frequency`, `time_constant`, `sensitivity`, readouts

### Concrete Nodes (`signal_chain_nodes.py`)

- `MFLISource`: Delegates to MFLI oscillator parameters
- `ManualVITransformer`: Manual transconductance parameters
- `ManualVoltagePreamp`: Manual gain parameters  
- `MFLILockIn`: Delegates to MFLI demod parameters

### Virtual Instrument (`signal_chain.py`)

- `SignalChain`: Unified front-panel interface with current control

## Signal Chain Parameters

### Control Parameters
- `I_set` (A): Target current setpoint (computes source voltage via gm)
- `reference_frequency` (Hz): Coupled source/demod frequency
- `excitation_v_ac` (V): Source amplitude (delegated)
- `output_on`: Source enable (delegated)

### Manual Setup Parameters  
- `gm_a_per_v` (A/V): V→I transconductance
- `vi_invert`: V→I polarity invert
- `preamp_gain` (V/V): Preamp voltage gain  
- `preamp_invert`: Preamp polarity invert
- `R_est` (Ω): Sample resistance estimate
- `margin`: Safety margin for guards (default 3.0)

### Lock-in Parameters (Delegated)
- `time_constant` (s): Integration time
- `sensitivity` (V): Input sensitivity  
- `input_range` (V): Input range
- `X`, `Y`, `R`, `Theta`: Readouts

### Derived Parameters (Read-only)
- `I_cmd` (A): Commanded current from source settings
- `V_sample_ac_meas` (V): Sample voltage corrected for preamp gain
- `I_meas` (A): Measured current from V_sample and R_est
- `recommended_sensitivity` (V): Suggested sensitivity = margin × R

## Guard Functions

The signal chain includes automatic protection against input overloads:

```python
# Predicts lock-in input voltage
V_predicted = |I_target| × R_est × |preamp_gain|

# Warns if predicted input > 80% of input_range
if V_predicted > 0.8 × input_range:
    print("[guard] Predicted input exceeds 80% of range")
```

## Units and Conventions

- **Amplitudes**: RMS by default (configurable via `amplitude_convention`)
- **Frequencies**: Hz
- **Currents**: Amperes (A)  
- **Voltages**: Volts (V)
- **Resistances**: Ohms (Ω)
- **Time**: Seconds (s)

## Safety Notes

- Always set `R_est` for meaningful current measurements and guard protection
- Guard functions are advisory only - they print warnings but don't block operations
- Manual parameters must be set correctly for your physical setup
- Open-loop current control relies on accurate transconductance calibration

## Example Topology Values

For a typical measurement setup:
- `gm_a_per_v = 1e-3` (1 mA/V V→I transformer)
- `preamp_gain = 100.0` (100 V/V preamp)  
- `R_est = 10e3` (10 kΩ sample)
- `I_set = 1e-6` (1 µA measurement current)

This results in:
- Source amplitude: 1 mV RMS
- Sample voltage: 10 mV  
- Preamp output: 1 V
- Well within typical ±1-10V lock-in ranges

## See Also

- `docs/examples/virtual/IVVI_rack_signal_chain.ipynb`: Complete usage example
- `tests/virtual/`: Comprehensive test suite
- Abstract base classes for extending to other topologies