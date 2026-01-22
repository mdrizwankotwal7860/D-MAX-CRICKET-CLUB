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

        # List of new columns to add
        new_columns = [
            ("number_of_teams", "INT DEFAULT 0"),
            ("match_format", "VARCHAR(50)"),
            ("rules_regulations", "TEXT"),
            ("contact_info", "VARCHAR(100)"),
            ("status", "ENUM('upcoming', 'ongoing', 'completed') DEFAULT 'upcoming'")
        ]

        print("Checking and updating 'tournaments' table...")

        for col_name, col_def in new_columns:
            try:
                # Try adding the column. If it exists, it will fail, which is fine.
                query = f"ALTER TABLE tournaments ADD COLUMN {col_name} {col_def}"
                cursor.execute(query)
                print(f"Added column: {col_name}")
            except mysql.connector.Error as err:
                if err.errno == 1060: # Key 'column_name' already exists
                    print(f"Column '{col_name}' already exists. Skipping.")
                else:
                    print(f"Error adding column '{col_name}': {err}")

        conn.commit()
        cursor.close()
        conn.close()
        print("Schema update completed successfully.")

    except mysql.connector.Error as err:
        print(f"Database Error: {err}")

if __name__ == "__main__":
    update_schema()
