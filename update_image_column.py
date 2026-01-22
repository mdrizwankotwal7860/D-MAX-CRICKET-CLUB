"""
Script to update tournaments table:
- Rename image_url column to image
- This stores just the filename, not full URL
"""
import mysql.connector
from config import Config

def update_tournaments_table():
    try:
        conn = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB
        )
        cursor = conn.cursor()
        
        # Check if image_url column exists
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'tournaments' 
            AND COLUMN_NAME = 'image_url'
        """, (Config.MYSQL_DB,))
        
        if cursor.fetchone():
            # Rename image_url to image
            cursor.execute("ALTER TABLE tournaments CHANGE image_url image VARCHAR(255)")
            conn.commit()
            print("Column 'image_url' renamed to 'image' successfully!")
        else:
            # Check if image column exists
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = %s 
                AND TABLE_NAME = 'tournaments' 
                AND COLUMN_NAME = 'image'
            """, (Config.MYSQL_DB,))
            
            if cursor.fetchone():
                print("Column 'image' already exists.")
            else:
                # Add image column
                cursor.execute("ALTER TABLE tournaments ADD COLUMN image VARCHAR(255)")
                conn.commit()
                print("Column 'image' added successfully!")
        
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        print(f"Error: {err}")

if __name__ == "__main__":
    update_tournaments_table()
