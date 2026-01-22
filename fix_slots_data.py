
import mysql.connector
from config import Config

def fix_slots():
    try:
        conn = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB
        )
        cursor = conn.cursor()
        
        # 1. Detach bookings from slots (since we made it nullable)
        print("Detaching bookings from slots...")
        cursor.execute("UPDATE bookings SET slot_id = NULL")
        
        # 2. Clear slots
        print("Clearing slots...")
        try:
            cursor.execute("DELETE FROM slots")
        except mysql.connector.Error as err:
            print(f"Delete failed: {err}")
            return

        # 3. Populate Hourly Slots (06:00 to 23:00)
        print("Populating hourly slots 06:00 to 23:00...")
        slots_data = []
        for h in range(6, 23):
            start_t = f"{h:02d}:00:00"
            end_t = f"{h+1:02d}:00:00"
            # (start, end)
            slots_data.append((start_t, end_t))
        
        cursor.executemany("INSERT INTO slots (start_time, end_time, is_active) VALUES (%s, %s, TRUE)", slots_data)
        
        conn.commit()
        print(f"Success: Inserted {len(slots_data)} hourly slots.")
        
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        print(f"Database Error: {err}")

if __name__ == "__main__":
    fix_slots()
