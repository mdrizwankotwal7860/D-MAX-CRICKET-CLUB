
import mysql.connector
from config import Config
from datetime import datetime, timedelta

def update_schema():
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB
        )
        cursor = conn.cursor()

        # 1. Create Slots Table
        print("Creating 'slots' table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS slots (
                id INT AUTO_INCREMENT PRIMARY KEY,
                start_time TIME NOT NULL,
                end_time TIME NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                UNIQUE(start_time, end_time)
            )
        """)

        # 2. Populate Initial Slots (6 AM to 11 PM)
        print("Populating initial slots...")
        start_hour = 6
        end_hour = 23
        
        # Check if slots exist
        cursor.execute("SELECT COUNT(*) FROM slots")
        count = cursor.fetchone()[0]
        
        if count == 0:
            slots_data = []
            for h in range(start_hour, end_hour):
                start_t = f"{h:02d}:00:00"
                end_t = f"{h+1:02d}:00:00"
                slots_data.append((start_t, end_t))
            
            cursor.executemany("INSERT INTO slots (start_time, end_time) VALUES (%s, %s)", slots_data)
            print(f"Inserted {len(slots_data)} slots.")
        else:
            print("Slots already populated.")

        # Get a fallback slot ID for existing bookings
        cursor.execute("SELECT id FROM slots LIMIT 1")
        fallback_slot_id = cursor.fetchone()[0]

        # 3. Alter Bookings Table
        print("Altering 'bookings' table...")
        
        # Helper to check if column exists
        def column_exists(table, col):
            cursor.execute(f"SHOW COLUMNS FROM {table} LIKE '{col}'")
            return cursor.fetchone() is not None

        # Add customer_email
        if not column_exists('bookings', 'customer_email'):
            print("Adding customer_email column...")
            cursor.execute("ALTER TABLE bookings ADD customer_email VARCHAR(255) NOT NULL DEFAULT 'no_email@example.com'")
            # Remove default afterwards? keeping it simple for migration
            cursor.execute("ALTER TABLE bookings ALTER COLUMN customer_email DROP DEFAULT")

        # Add slot_id
        if not column_exists('bookings', 'slot_id'):
            print("Adding slot_id column...")
            # Add as nullable first, or with default
            cursor.execute(f"ALTER TABLE bookings ADD slot_id INT NOT NULL DEFAULT {fallback_slot_id}")
            cursor.execute("ALTER TABLE bookings ALTER COLUMN slot_id DROP DEFAULT")
            
            # Add Foreign Key
            try:
                cursor.execute("ALTER TABLE bookings ADD CONSTRAINT fk_slot FOREIGN KEY (slot_id) REFERENCES slots(id)")
                print("Foreign key fk_slot added.")
            except mysql.connector.Error as err:
                 if err.errno == 1061: # Duplicate key name
                     print("Foreign key fk_slot already exists.")
                 else:
                     raise err

        # Update Status Enum
        # We need to modify the ENUM definition.
        # Current: 'pending', 'confirmed', 'cancelled'
        # New: 'PENDING', 'CONFIRMED', 'REJECTED' (User requested UPPERCASE but let's stick to lowercase consistency if possible, 
        # or STRICTLY follow requirements. User prompts: PENDING, CONFIRMED, REJECTED (Title Case in UI, but maybe Enum value?).
        # The SQL snippet in prompt used UPPERCASE: ENUM('PENDING','CONFIRMED','REJECTED').
        # I wll follow the prompt strictly.
        
        print("Updating status ENUM...")
        # Note: changing ENUM values might cause data loss if existing values don't match.
        # Existing: pending, confirmed, cancelled.
        # New: PENDING, CONFIRMED, REJECTED.
        # Strategy: Update existing rows to match new format FIRST, then ALTER.
        
        cursor.execute("UPDATE bookings SET status = 'PENDING' WHERE status = 'pending'")
        cursor.execute("UPDATE bookings SET status = 'CONFIRMED' WHERE status = 'confirmed'")
        cursor.execute("UPDATE bookings SET status = 'REJECTED' WHERE status = 'cancelled'")
        
        # Now Alter
        cursor.execute("ALTER TABLE bookings MODIFY COLUMN status ENUM('PENDING', 'CONFIRMED', 'REJECTED') DEFAULT 'PENDING'")

        conn.commit()
        print("Schema update completed successfully!")

    except mysql.connector.Error as err:
        print(f"Error: {err}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    update_schema()
