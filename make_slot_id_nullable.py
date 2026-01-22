
import mysql.connector
from config import Config

def make_slot_id_nullable():
    try:
        conn = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB
        )
        cursor = conn.cursor()
        
        print("Altering bookings table to make slot_id nullable...")
        # Check FK constraint name first?
        # Usually modifying the column is enough, unless FK is strict.
        # Ensure we keep the FK but allow NULL.
        
        # MySQL syntax: ALTER TABLE bookings MODIFY slot_id INT NULL;
        cursor.execute("ALTER TABLE bookings MODIFY slot_id INT NULL")
        
        conn.commit()
        print("Success: slot_id is now nullable.")
        
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        print(f"Error: {err}")

if __name__ == "__main__":
    make_slot_id_nullable()
