# debug_import.py
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Try to import the simulator module itself
try:
    import simulations.simulator as sim_module
    print("✓ Successfully imported simulator module")
    print(f"Contents: {dir(sim_module)}")
except Exception as e:

    print(f"✗ Failed to import module: {e}")
