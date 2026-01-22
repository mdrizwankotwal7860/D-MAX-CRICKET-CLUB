
import mysql.connector
from config import Config

def kill_locks():
    try:
        conn = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB
        )
        cursor = conn.cursor(dictionary=True)
        
        print("Checking process list...")
        cursor.execute("SHOW FULL PROCESSLIST")
        processes = cursor.fetchall()
        
        my_id = conn.connection_id
        print(f"My Connection ID: {my_id}")
        
        for p in processes:
            pid = p['Id']
            user = p['User']
            db = p['db']
            state = p['State']
            info = p['Info']
            
            if pid != my_id and db == Config.MYSQL_DB:
                print(f"Killing process {pid} (User: {user}, State: {state}, Info: {info})")
                try:
                    cursor.execute(f"KILL {pid}")
                    print(f"Killed {pid}")
                except Exception as e:
                    print(f"Failed to kill {pid}: {e}")
            else:
                print(f"Skipping {pid} (Self or unrelated)")
                
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        print(f"Error: {err}")

if __name__ == "__main__":
    kill_locks()
