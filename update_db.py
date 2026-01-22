import mysql.connector
from config import Config

def update_db():
    print("Connecting to database...")
    try:
        conn = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB
        )
        cursor = conn.cursor()
        
        print("Creating 'admins' table if not exists...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL
            );
        """)
        
        print("Inserting default admin user...")
        # Insert 'admin' / 'admin123' if not exists
        cursor.execute("SELECT * FROM admins WHERE username = 'admin'")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO admins (username, password) VALUES ('admin', 'admin123')")
            print("Default admin user created.")
        else:
            print("Admin user already exists.")
            
        conn.commit()
        cursor.close()
        conn.close()
        print("Database update successful!")
        
    except mysql.connector.Error as err:
        print(f"Error: {err}")

if __name__ == "__main__":
    update_db()
