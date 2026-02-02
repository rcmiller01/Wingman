from proxmoxer import ProxmoxAPI
import os
from dotenv import load_dotenv

load_dotenv()

host_raw = os.getenv("PROXMOX_HOST", "192.168.50.158:8006")
host = host_raw.replace("https://", "").replace("http://", "").split(":")[0]
port_str = host_raw.split(":")[-1] if ":" in host_raw else "8006"
port = int(port_str)

user = os.getenv("PROXMOX_USER", "root@pam")
token_name = os.getenv("PROXMOX_TOKEN_NAME", "wingman")
token_value = os.getenv("PROXMOX_TOKEN_VALUE", "e8e6bfed-dfbe-4a69-b869-bc572aeb34c2")
verify_ssl = os.getenv("PROXMOX_VERIFY_SSL", "false").lower() == "true"

print(f"Testing connection to {host} port {port} as {user} with token {token_name}")

def test_api(name, **kwargs):
    print(f"\n--- Testing {name} ---")
    try:
        api = ProxmoxAPI(host, port=port, verify_ssl=verify_ssl, timeout=10, **kwargs)
        nodes = api.nodes.get()
        print(f"SUCCESS {name}: Connected!")
        print(f"Nodes: {[n['node'] for n in nodes]}")
        return True
    except Exception as e:
        print(f"FAILED {name}: {e}")
        return False

# Test 1: Standard Token args with explicit port
test_api("Standard Token", user=user, token_name=token_name, token_value=token_value)

# Test 2: Full user string in 'user' field, token in 'token_value'
test_api("Full User String", user=f"{user}!{token_name}", token_value=token_value)

# Test 3: Standard with host=host:port (no explicit port arg)
print("\n--- Testing Host:Port String ---")
try:
    api = ProxmoxAPI(f"{host}:{port}", user=user, token_name=token_name, token_value=token_value, verify_ssl=verify_ssl, timeout=10)
    nodes = api.nodes.get()
    print("SUCCESS Host:Port String: Connected!")
except Exception as e:
    print(f"FAILED Host:Port String: {e}")
