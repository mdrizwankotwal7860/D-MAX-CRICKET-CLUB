
import mysql.connector
from config import Config

def check_schema():
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
        print("Columns in 'bookings' table:")
        for col in columns:
            print(f"- {col['Field']} ({col['Type']})")
        
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        print(f"Error: {err}")

if __name__ == "__main__":
    check_schema()
