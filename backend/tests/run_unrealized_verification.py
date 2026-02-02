
import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")

# Import tests
from tests.test_integration import test_full_incident_remediation_flow, test_policy_denylisting, test_policy_rate_limiting

async def run_tests():
    print("[Verify] Running test_policy_denylisting...")
    try:
        await test_policy_denylisting()
        print("[Verify] PASS: test_policy_denylisting")
    except Exception as e:
        print(f"[Verify] FAIL: test_policy_denylisting - {e}")
        import traceback
        traceback.print_exc()

    print("\n[Verify] Running test_policy_rate_limiting...")
    try:
        await test_policy_rate_limiting()
        print("[Verify] PASS: test_policy_rate_limiting")
    except Exception as e:
        print(f"[Verify] FAIL: test_policy_rate_limiting - {e}")
        import traceback; traceback.print_exc()


    print("\n[Verify] Running test_full_incident_remediation_flow...")
    try:
        await test_full_incident_remediation_flow()
        print("[Verify] PASS: test_full_incident_remediation_flow")
    except Exception as e:
        print(f"[Verify] FAIL: test_full_incident_remediation_flow - {e}")
        import traceback; traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_tests())
