#!/usr/bin/env python3
"""
Simple test script to verify the PeakTech15xx simulation file works correctly.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Create a minimal test to check if the missing command is now handled
try:
    # Directly test the simulation file format
    import yaml
    
    with open('src/qcodes_contrib_drivers/sims/PeakTech15xx.yaml', 'r') as f:
        sim_data = yaml.safe_load(f)
    
    print("Simulation file contents:")
    print(yaml.dump(sim_data, default_flow_style=False))
    
    # Check if our new command is present
    dialogues = sim_data['devices']['PeakTech15xx']['dialogues']
    sens_func_found = False
    for dialogue in dialogues:
        if dialogue['q'] == ':SENS:FUNC?':
            sens_func_found = True
            print(f"Found :SENS:FUNC? command with response: {dialogue['r']}")
            break
    
    if not sens_func_found:
        print("ERROR: :SENS:FUNC? command not found in simulation file")
        sys.exit(1)
    else:
        print("SUCCESS: :SENS:FUNC? command properly added to simulation file")
        
except Exception as e:
    print(f"Error testing simulation file: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)