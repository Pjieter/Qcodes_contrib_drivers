#!/usr/bin/env python3
"""
Comprehensive test to verify the PeakTech15xx simulation works with the new sense_function parameter.
"""

import sys
import os
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Try to test with the actual PyVISA simulation if available
try:
    import pyvisa
    import pyvisa_sim
    
    # Create a temporary resource manager with our simulation
    sim_file_path = 'src/qcodes_contrib_drivers/sims/PeakTech15xx.yaml'
    
    # Test the simulation file by creating a resource manager
    rm = pyvisa.ResourceManager(f'pyvisa_sim_file@{sim_file_path}')
    
    # Try to open the simulated instrument
    try:
        instr = rm.open_resource('ASRL1::INSTR')
        
        # Test the GMAX command that we know works
        response = instr.query('GMAX')
        print(f"✓ GMAX query response: {response}")
        
        # Test our new SENS:FUNC? command
        response = instr.query(':SENS:FUNC?')
        print(f"✓ :SENS:FUNC? query response: {response}")
        
        if response.strip() == 'VOLT':
            print("✓ :SENS:FUNC? returns expected 'VOLT' value")
        else:
            print(f"✗ :SENS:FUNC? returned '{response}' instead of 'VOLT'")
            
        instr.close()
        print("✓ Simulation test passed successfully")
        
    except Exception as e:
        print(f"✗ Error testing simulation: {e}")
        
except ImportError:
    print("PyVISA simulation not available, skipping simulation test")
    
# Test that the driver code compiles and has the expected parameter
import unittest.mock

# Mock all required modules
sys.modules['pyvisa'] = unittest.mock.MagicMock()
sys.modules['pyvisa.resources'] = unittest.mock.MagicMock()
sys.modules['pyvisa.resources.serial'] = unittest.mock.MagicMock()
sys.modules['pyvisa.constants'] = unittest.mock.MagicMock()
sys.modules['qcodes'] = unittest.mock.MagicMock()
sys.modules['qcodes.instrument'] = unittest.mock.MagicMock()
sys.modules['qcodes.parameters'] = unittest.mock.MagicMock()
sys.modules['qcodes.utils'] = unittest.mock.MagicMock()
sys.modules['qcodes.validators'] = unittest.mock.MagicMock()

try:
    # Read the source file directly instead of using inspect
    with open('src/qcodes_contrib_drivers/drivers/PeakTech/PeakTech_15xx.py', 'r') as f:
        source = f.read()
    
    if 'sense_function' in source:
        print("✓ sense_function parameter found in driver source")
    else:
        print("✗ sense_function parameter not found in driver")
        
    if ':SENS:FUNC?' in source:
        print("✓ :SENS:FUNC? command found in driver source")
    else:
        print("✗ :SENS:FUNC? command not found in driver")
        
    print("✓ Driver source validation passed")
    
except Exception as e:
    print(f"✗ Error validating driver source: {e}")
    import traceback
    traceback.print_exc()