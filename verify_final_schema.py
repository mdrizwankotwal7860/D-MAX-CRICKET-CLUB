
import mysql.connector
from config import Config

def verify_schema():
    try:
        conn = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute("DESCRIBE bookings")
        columns = cursor.fetchall()
        
        expected = {
            'payment_status': "enum('pending','paid_manual_verification','paid_verified','rejected')",
            'payment_uploaded_at': 'timestamp',
            'customer_phone': 'varchar(20)',
            'status': "enum('pending','confirmed','cancelled')"
        }
        
        print("Verifying Schema...")
        for col in columns:
            name = col['Field']
            type_val = col['Type']
            # Decode bytes if needed (mysql connector sometimes returns bytes for types)
            if isinstance(type_val, bytes):
                type_val = type_val.decode('utf-8')
            
            if name in expected:
                if expected[name] in type_val:
                    print(f"[OK] {name}: {type_val}")
                else:
                    print(f"[FAIL] {name}: Expected {expected[name]}, Got {type_val}")
                    
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        print(f"Error: {err}")

if __name__ == "__main__":
    verify_schema()
