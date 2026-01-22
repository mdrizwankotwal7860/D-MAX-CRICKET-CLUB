
import mysql.connector
from config import Config

def add_payment_columns():
    try:
        conn = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB
        )
        cursor = conn.cursor()

        # Add payment_image column
        try:
            cursor.execute("ALTER TABLE bookings ADD COLUMN payment_image VARCHAR(255)")
            print("Added payment_image column successfully")
        except mysql.connector.Error as err:
            print(f"Error adding payment_image column (might already exist): {err}")

        # Add payment_status column
        try:
            cursor.execute("ALTER TABLE bookings ADD COLUMN payment_status ENUM('pending', 'paid_manual_verification') DEFAULT 'pending'")
            print("Added payment_status column successfully")
        except mysql.connector.Error as err:
            print(f"Error adding payment_status column (might already exist): {err}")

        # Add payment_uploaded_at column
        try:
            cursor.execute("ALTER TABLE bookings ADD COLUMN payment_uploaded_at TIMESTAMP NULL DEFAULT NULL")
            print("Added payment_uploaded_at column successfully")
        except mysql.connector.Error as err:
            print(f"Error adding payment_uploaded_at column (might already exist): {err}")

        conn.commit()
        cursor.close()
        conn.close()
        print("Schema update completed")

    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")

if __name__ == "__main__":
    add_payment_columns()
