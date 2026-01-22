
import mysql.connector
from config import Config

def clean_data():
    try:
        conn = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB
        )
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bookings WHERE customer_name = 'Test User'")
        conn.commit()
        print("Cleaned test data.")
        conn.close()
    except Exception as e:
        print(e)

if __name__ == "__main__":
    clean_data()
