import httpx
import os
from dotenv import load_dotenv
import json

load_dotenv()

host_raw = os.getenv("PROXMOX_HOST", "192.168.50.158:8006")
host = host_raw.replace("https://", "").replace("http://", "")
if ":" not in host:
    host = f"{host}:8006"

url = f"https://{host}/api2/json/nodes"
user = os.getenv("PROXMOX_USER", "root@pam")
token_name = os.getenv("PROXMOX_TOKEN_NAME", "wingman")
token_value = os.getenv("PROXMOX_TOKEN_VALUE", "e8e6bfed-dfbe-4a69-b869-bc572aeb34c2")

token_id = f"{user}!{token_name}"
# Proxmox API Token header format: PVEAPIToken=USER!TOKENID=SECRET
auth_header = f"PVEAPIToken={token_id}={token_value}"

print(f"Direct request to {url}")
print(f"Auth Header: {auth_header}")

try:
    with httpx.Client(verify=False, timeout=10) as client:
        response = client.get(url, headers={"Authorization": auth_header})
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("SUCCESS: Direct API connection worked!")
        else:
            print(f"FAILED: Status {response.status_code}")
except Exception as e:
    print(f"ERROR: {e}")
