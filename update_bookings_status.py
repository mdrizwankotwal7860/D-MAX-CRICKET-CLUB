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
        
        # Modify the status column to include 'pending_verification' and 'rejected', and set default to 'pending_verification'
        # We also treat 'pending' as 'pending_verification' for backward compatibility or migration if needed.
        # But here we will explicitly update the ENUM.
        
        print("Updating bookings table schema...")
        
        # Alter table to update ENUM definition
        # Note: changing ENUM can be tricky if data exists, but we are adding values.
        # We'll include 'pending' and 'confirmed' and 'cancelled' to keep existing data safe, add 'pending_verification' and 'rejected'.
        
        alter_query = """
        ALTER TABLE bookings 
        MODIFY COLUMN status ENUM('pending', 'confirmed', 'cancelled', 'pending_verification', 'rejected') DEFAULT 'pending_verification'
        """
        cursor.execute(alter_query)
        print("Successfully updated status column ENUM.")
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Schema update complete.")
        
    except mysql.connector.Error as err:
        print(f"Error: {err}")

if __name__ == '__main__':
    update_schema()
