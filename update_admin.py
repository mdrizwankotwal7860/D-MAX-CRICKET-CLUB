"""
Script to update admin credentials in the database.
Run this once to change admin username and password.
"""
import mysql.connector
from config import Config

def update_admin_credentials():
    try:
        conn = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB
        )
        cursor = conn.cursor()
        
        # Update admin credentials
        new_username = 'cricket'
        new_password = 'cricket@123'
        
        cursor.execute(
            "UPDATE admins SET username = %s, password = %s WHERE id = 1",
            (new_username, new_password)
        )
        conn.commit()
        
        if cursor.rowcount > 0:
            print(f"Admin credentials updated successfully!")
            print(f"New Username: {new_username}")
            print(f"New Password: {new_password}")
        else:
            # If no row was updated, insert a new admin
            cursor.execute(
                "INSERT INTO admins (username, password) VALUES (%s, %s)",
                (new_username, new_password)
            )
            conn.commit()
            print(f"New admin created!")
            print(f"Username: {new_username}")
            print(f"Password: {new_password}")
        
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        print(f"Error: {err}")

if __name__ == "__main__":
    update_admin_credentials()
