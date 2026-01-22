import mysql.connector
from config import Config

def add_paid_amount_column():
    try:
        conn = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB
        )
        cursor = conn.cursor()

        # Add paid_amount column
        try:
            cursor.execute("ALTER TABLE bookings ADD COLUMN paid_amount DECIMAL(10,2) DEFAULT 0.00 AFTER total_price")
            print("Added paid_amount column successfully")
        except mysql.connector.Error as err:
            if err.errno == 1060:
                print(f"Column paid_amount already exists.")
            else:
                print(f"Error adding paid_amount column: {err}")

        conn.commit()
        cursor.close()
        conn.close()
        print("Schema update completed")

    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")

if __name__ == "__main__":
    add_paid_amount_column()
