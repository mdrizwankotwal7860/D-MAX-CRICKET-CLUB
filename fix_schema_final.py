
import mysql.connector
from config import Config

def fix_schema():
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB
        )
        cursor = conn.cursor()

        print("Fixing customer_phone...")
        cursor.execute("ALTER TABLE bookings MODIFY COLUMN customer_phone VARCHAR(20) NOT NULL")
        
        print("Fixing payment_status...")
        cursor.execute("ALTER TABLE bookings MODIFY COLUMN payment_status ENUM('pending', 'paid_manual_verification', 'paid_verified', 'rejected') DEFAULT 'pending'")
        
        print("Fixing status...")
        cursor.execute("ALTER TABLE bookings MODIFY COLUMN status ENUM('pending', 'confirmed', 'cancelled') DEFAULT 'confirmed'")
        
        conn.commit()
        print("Schema fixes applied successfully!")

    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    fix_schema()
