
import mysql.connector
from config import Config

def fix_status():
    conn = mysql.connector.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB
    )
    cursor = conn.cursor()
    try:
        print("Fixing status column...")
        # 1. Temporarily change to VARCHAR to allow any value
        cursor.execute("ALTER TABLE bookings MODIFY status VARCHAR(50)")
        
        # 2. Normalize values to Upper Case
        cursor.execute("UPDATE bookings SET status = UPPER(status)")
        
        # 3. Handle mappings if needed (e.g. 'paid' -> 'CONFIRMED' if valid?)
        # For now, just ensuring standard values
        
        # 4. Alter back to new ENUM
        cursor.execute("ALTER TABLE bookings MODIFY COLUMN status ENUM('PENDING', 'CONFIRMED', 'REJECTED') DEFAULT 'PENDING'")
        
        conn.commit()
        print("Status column fixed successfully.")
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    fix_status()
