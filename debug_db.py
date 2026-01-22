import mysql.connector
from config import Config

def debug_database():
    try:
        conn = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB
        )
        cursor = conn.cursor()

        print("--- Tables in Database ---")
        cursor.execute("SHOW TABLES")
        for (table,) in cursor.fetchall():
            print(table)

        print("\n--- Bookings Table Schema ---")
        cursor.execute("DESCRIBE bookings")
        for col in cursor.fetchall():
            print(col)

        print("\n--- Tournaments Table Schema ---")
        cursor.execute("DESCRIBE tournaments")
        for col in cursor.fetchall():
            print(col)

        print("\n--- Tournament Registrations Table Schema ---")
        try:
            cursor.execute("DESCRIBE tournament_registrations")
            for col in cursor.fetchall():
                print(col)
        except mysql.connector.Error as err:
            print(f"Error describing tournament_registrations: {err}")

        conn.close()

    except mysql.connector.Error as err:
        print(f"Connection Error: {err}")

if __name__ == "__main__":
    debug_database()
