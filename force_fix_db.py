
import mysql.connector
from config import Config

def force_fix():
    conn = mysql.connector.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB
    )
    cursor = conn.cursor()
    try:
        print("Force fixing status column...")
        # Disable strict mode to allow truncation/conversion if needed
        cursor.execute("SET SESSION sql_mode = ''")
        
        # 1. Change to TEXT (very permissible)
        cursor.execute("ALTER TABLE bookings MODIFY COLUMN status TEXT")
        print("Converted to TEXT")
        
        # 2. Update Data
        cursor.execute("UPDATE bookings SET status = UPPER(status)")
        # Map specific old values just in case
        cursor.execute("UPDATE bookings SET status = 'PENDING' WHERE status NOT IN ('PENDING', 'CONFIRMED', 'REJECTED')")
        print("Data Updated")
        
        # 3. Change to new ENUM
        cursor.execute("ALTER TABLE bookings MODIFY COLUMN status ENUM('PENDING', 'CONFIRMED', 'REJECTED') DEFAULT 'PENDING'")
        print("Converted to ENUM")
        
        conn.commit()
        print("Success!")
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    force_fix()
