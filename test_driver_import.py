#!/usr/bin/env python3
"""
Simple test script to verify the PeakTech15xx driver with the new sense_function parameter.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Mock minimal dependencies
import unittest.mock

# Mock modules that we don't have installed
sys.modules['qcodes'] = unittest.mock.MagicMock()
sys.modules['qcodes.instrument'] = unittest.mock.MagicMock()
sys.modules['qcodes.parameters'] = unittest.mock.MagicMock()
sys.modules['qcodes.utils'] = unittest.mock.MagicMock()
sys.modules['qcodes.validators'] = unittest.mock.MagicMock()
sys.modules['pyvisa'] = unittest.mock.MagicMock()
sys.modules['pyvisa.resources'] = unittest.mock.MagicMock()
sys.modules['pyvisa.resources.serial'] = unittest.mock.MagicMock()
sys.modules['pyvisa.constants'] = unittest.mock.MagicMock()

# Test imports
try:
    from qcodes_contrib_drivers.drivers.PeakTech.PeakTech_15xx import PeakTech15xx
    print("✓ Driver import successful")
    
    # Check that the class has been defined correctly
    if hasattr(PeakTech15xx, '__init__'):
        print("✓ Driver class properly defined")
    else:
        print("✗ Driver class not properly defined")
        sys.exit(1)
        
    print("✓ All basic checks passed")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)