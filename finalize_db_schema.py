import mysql.connector
from config import Config

def migrate_db():
    print("Starting Database Migration...")
    try:
        conn = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB
        )
        cursor = conn.cursor()
        
        # Helper to check if column exists
        def column_exists(table, column):
            cursor.execute(f"SHOW COLUMNS FROM {table} LIKE '{column}'")
            return cursor.fetchone() is not None

        # 1. Check for start_time / booking_time
        if column_exists('bookings', 'booking_time') and not column_exists('bookings', 'start_time'):
            print("Renaming booking_time to start_time...")
            try:
                cursor.execute("ALTER TABLE bookings CHANGE booking_time start_time TIME NOT NULL")
                print("Renamed successfully.")
            except Exception as e:
                print(f"Error renaming: {e}")
        elif not column_exists('bookings', 'start_time'):
             print("Adding start_time column...")
             try:
                cursor.execute("ALTER TABLE bookings ADD COLUMN start_time TIME NOT NULL")
                print("Added start_time.")
             except Exception as e:
                print(f"Error adding start_time: {e}")

        # 2. Add total_price
        if not column_exists('bookings', 'total_price'):
            print("Adding total_price column...")
            try:
                cursor.execute("ALTER TABLE bookings ADD COLUMN total_price DECIMAL(10, 2) DEFAULT 0.00")
                print("Added total_price.")
            except Exception as e:
                print(f"Error adding total_price: {e}")

        # 3. Add paid_amount
        if not column_exists('bookings', 'paid_amount'):
            print("Adding paid_amount column...")
            try:
                cursor.execute("ALTER TABLE bookings ADD COLUMN paid_amount DECIMAL(10, 2) DEFAULT 0.00")
                print("Added paid_amount.")
            except Exception as e:
                print(f"Error adding paid_amount: {e}")

        # 4. Add payment_image
        if not column_exists('bookings', 'payment_image'):
            print("Adding payment_image column...")
            try:
                cursor.execute("ALTER TABLE bookings ADD COLUMN payment_image VARCHAR(255)")
                print("Added payment_image.")
            except Exception as e:
                print(f"Error adding payment_image: {e}")

        # 5. Add payment_status
        if not column_exists('bookings', 'payment_status'):
            print("Adding payment_status column...")
            try:
                cursor.execute("ALTER TABLE bookings ADD COLUMN payment_status ENUM('pending', 'paid_manual_verification') DEFAULT 'pending'")
                print("Added payment_status.")
            except Exception as e:
                print(f"Error adding payment_status: {e}")

        # 6. Add payment_uploaded_at
        if not column_exists('bookings', 'payment_uploaded_at'):
            print("Adding payment_uploaded_at column...")
            try:
                cursor.execute("ALTER TABLE bookings ADD COLUMN payment_uploaded_at TIMESTAMP NULL DEFAULT NULL")
                print("Added payment_uploaded_at.")
            except Exception as e:
                print(f"Error adding payment_uploaded_at: {e}")

        conn.commit()
        cursor.close()
        conn.close()
        print("Migration Completed Successfully.")
        
    except mysql.connector.Error as err:
        print(f"Database Error: {err}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    migrate_db()
