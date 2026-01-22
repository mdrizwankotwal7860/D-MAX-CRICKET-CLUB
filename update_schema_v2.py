
import mysql.connector
from config import Config

def update_schema():
    try:
        conn = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB
        )
        cursor = conn.cursor()

        print("Updating payment_status ENUM...")
        # Add 'paid_verified' and 'rejected' to ENUM
        try:
            cursor.execute("ALTER TABLE bookings MODIFY COLUMN payment_status ENUM('pending', 'paid_manual_verification', 'paid_verified', 'rejected') DEFAULT 'pending'")
            print("Successfully updated payment_status ENUM.")
        except mysql.connector.Error as err:
            print(f"Error updating payment_status: {err}")

        print("Updating customer_phone length...")
        try:
            cursor.execute("ALTER TABLE bookings MODIFY COLUMN customer_phone VARCHAR(20) NOT NULL")
            print("Successfully updated customer_phone length.")
        except mysql.connector.Error as err:
            print(f"Error updating customer_phone: {err}")
            
        print("Updating status ENUM to include 'cancelled' if not present...")
        try:
             # Check if 'cancelled' is already there, usually MODIFY COLUMN replaces the whole definition so we just define what we want
             cursor.execute("ALTER TABLE bookings MODIFY COLUMN status ENUM('pending', 'confirmed', 'cancelled') DEFAULT 'confirmed'")
             print("Successfully updated status ENUM.")
        except mysql.connector.Error as err:
             print(f"Error updating status ENUM: {err}")

        conn.commit()
        cursor.close()
        conn.close()
        print("Schema update complete.")

    except mysql.connector.Error as err:
        print(f"Database connection failed: {err}")

if __name__ == "__main__":
    update_schema()
