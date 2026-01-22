
import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def verify():
    session = requests.Session()
    session.trust_env = False # Bypass proxy
    
    print("1. Checking Public Slots API...")
    try:
        res = session.get(f"{BASE_URL}/api/slots")
        if res.status_code == 200:
            slots = res.json()
            print(f"✅ Success: Fetched {len(slots)} slots.")
            if len(slots) > 0:
                print(f"   First slot: {slots[0]['display']} (ID: {slots[0]['id']})")
        else:
            print(f"❌ Failed: Status {res.status_code}")
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        return

    print("\n2. Checking Admin Slots Page (Login Bypass check if possible or just reachability)")
    # Since admin requires login, we just check if redirects to login
    try:
         res = session.get(f"{BASE_URL}/admin/slots", allow_redirects=False)
         if res.status_code == 302 and 'login' in res.headers['Location']:
             print("✅ Success: Protected route redirects to login.")
         else:
             print(f"⚠️ Warning: Route gave {res.status_code}")
    except Exception as e:
         print(f"❌ Failed: {e}")

if __name__ == "__main__":
    verify()
