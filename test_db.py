import mysql.connector
from config import Config
import sys

print("Testing database connection...")
print(f"Host: {Config.MYSQL_HOST}")
print(f"User: {Config.MYSQL_USER}")
print(f"DB:   {Config.MYSQL_DB}")

try:
    conn = mysql.connector.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB
    )
    if conn.is_connected():
        print("SUCCESS! Connected to MySQL database.")
        
        # Also check if table exists
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES LIKE 'bookings'")
        result = cursor.fetchone()
        if result:
            print("SUCCESS! Table 'bookings' found.")
            
            # Check columns
            cursor.execute("DESCRIBE bookings")
            columns = [row[0] for row in cursor.fetchall()]
            print(f"Columns: {columns}")
            if 'start_time' in columns:
                print("SUCCESS! Column 'start_time' found.")
            else:
                print("FAILURE! Column 'start_time' NOT found. Found: " + ", ".join(columns))
        else:
            print("FAILURE! Table 'bookings' NOT found.")
            
        conn.close()
        sys.exit(0)
except mysql.connector.Error as err:
    print(f"CONNECTION FAILED: {err}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
