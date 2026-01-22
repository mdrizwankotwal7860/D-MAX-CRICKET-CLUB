"""
Script to add missing image_url column to tournaments table.
"""
import mysql.connector
from config import Config

def fix_tournaments_table():
    try:
        conn = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB
        )
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'tournaments' 
            AND COLUMN_NAME = 'image_url'
        """, (Config.MYSQL_DB,))
        
        if cursor.fetchone():
            print("Column 'image_url' already exists.")
        else:
            # Add the missing column
            cursor.execute("ALTER TABLE tournaments ADD COLUMN image_url VARCHAR(255)")
            conn.commit()
            print("Column 'image_url' added successfully!")
        
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        print(f"Error: {err}")

if __name__ == "__main__":
    fix_tournaments_table()
