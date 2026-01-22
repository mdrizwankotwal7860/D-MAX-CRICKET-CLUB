import mysql.connector
from config import Config

def add_end_time_column():
    try:
        conn = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB
        )
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("SHOW COLUMNS FROM bookings LIKE 'end_time'")
        result = cursor.fetchone()
        
        if not result:
            print("Adding end_time column...")
            cursor.execute("ALTER TABLE bookings ADD COLUMN end_time TIME AFTER start_time")
            
            # Update existing rows
            print("Updating existing rows...")
            cursor.execute("UPDATE bookings SET end_time = ADDTIME(start_time, SEC_TO_TIME(duration_hours * 3600)) WHERE end_time IS NULL")
            
            conn.commit()
            print("Schema updated successfully.")
        else:
            print("Column end_time already exists.")
            
        cursor.close()
        conn.close()
        
    except mysql.connector.Error as err:
        print(f"Error: {err}")

if __name__ == "__main__":
    add_end_time_column()
