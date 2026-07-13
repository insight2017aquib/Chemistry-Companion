import sys
import logging
logging.basicConfig(level=logging.INFO)

try:
    from docking_workflow.interaction_analyzer import (
        METAL_COORDINATION_DISTANCE_CUTOFF, 
        WATER_BRIDGE_DISTANCE_CUTOFF,
        _looks_like_metal_coordinator
    )
    print("Successfully imported new constants!")
    print(f"Metal Cutoff: {METAL_COORDINATION_DISTANCE_CUTOFF}")
    print(f"Water Bridge Cutoff: {WATER_BRIDGE_DISTANCE_CUTOFF}")
    
    assert _looks_like_metal_coordinator("O1") == True
    assert _looks_like_metal_coordinator("N2") == True
    assert _looks_like_metal_coordinator("C3") == False
    
    print("Tests passed!")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
