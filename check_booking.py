
import mysql.connector
from config import Config

def check_booking():
    try:
        conn = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM bookings WHERE customer_name = 'Test User' ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            print("Booking Found:")
            print(row)
        else:
            print("No booking found.")
        conn.close()
    except Exception as e:
        print(e)

if __name__ == "__main__":
    check_booking()
