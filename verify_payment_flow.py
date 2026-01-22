
import requests
import datetime
import os

BASE_URL = "http://127.0.0.1:5000"

def test_flow():
    session = requests.Session()
    session.trust_env = False # Ignore proxies
    
    # 1. Admin Login (to get ready)
    print("--- 1. Logging in Admin ---")
    login_data = {'username': 'cricket', 'password': 'cricket@123'}
    res = session.post(f"{BASE_URL}/admin/login", data=login_data, timeout=5)
    if res.url.endswith('/admin/dashboard'):
        print("Admin login successful.")
    else:
        print("Admin login failed.")
        return

    # 2. Start Payment Timer (Get Token)
    print("\n--- 2. Initiating Payment ---")
    res = session.post(f"{BASE_URL}/api/initiate_payment", timeout=5)
    try:
        data = res.json()
        token = data.get('token')
        print("Payment token received.")
    except Exception as e:
        print(f"Failed to get token: {e}")
        return

    # 3. Create Booking with File Upload
    print("\n--- 3. Creating Booking ---")
    
    # Create a dummy image
    dummy_img_path = "test_payment.jpg"
    with open(dummy_img_path, "wb") as f:
        f.write(b"dummy image content")
        
    img_file = open(dummy_img_path, 'rb')
    files = {'payment_screenshot': (dummy_img_path, img_file, 'image/jpeg')}
    today = datetime.date.today().isoformat()
    
    booking_data = {
        'name': 'Test User',
        'phone': '9999999999',
        'email': 'test@example.com',
        'date': today,
        'start_time': '10:00',
        'end_time': '11:00',
        'paid_amount': '800',
        'payment_token': token
    }
    
    res = session.post(f"{BASE_URL}/api/book_slot", data=booking_data, files=files, timeout=10)
    img_file.close()
    print(f"Booking Status Code: {res.status_code}")
    print(f"Booking Response: {res.text}")
    
    if res.status_code == 200:
        booking_id = res.json().get('booking_id')
        print(f"Booking Created with ID: {booking_id}")
    else:
        print("Booking creation failed.")
        return

    # 4. Verify Admin Approval
    print(f"\n--- 4. Approving Booking {booking_id} ---")
    res = session.post(f"{BASE_URL}/admin/bookings/approve/{booking_id}", timeout=5)
    if res.status_code == 200:
        print("Approval request sent (redirected likely).")
    else:
        print(f"Approval failed: {res.status_code}")

    # 5. Cleanup
    os.remove(dummy_img_path)
    print("\nTest Flow Complete.")

if __name__ == "__main__":
    try:
        test_flow()
    except requests.exceptions.ConnectionError:
        print("Error: Flask app is not running. Please run 'python app.py' in a separate terminal.")
