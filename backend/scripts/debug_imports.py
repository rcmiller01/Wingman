
import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")

print("Importing models...")
try:
    from homelab.storage.models import Incident
    print("Models imported.")
except Exception as e:
    print(f"Failed to import models: {e}")

print("Importing policy_engine...")
try:
    from homelab.policy.policy_engine import policy_engine
    print("Policy Engine imported.")
except Exception as e:
    print(f"Failed to import policy_engine: {e}")

print("Importing control_plane...")
try:
    from homelab.control_plane.control_plane import control_plane
    print("Control Plane imported.")
except Exception as e:
    print(f"Failed to import control_plane: {e}")
