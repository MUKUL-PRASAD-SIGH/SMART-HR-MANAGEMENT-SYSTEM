import pymysql
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

def connect_db():
    try:
        connection = pymysql.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),  # Enter your MySQL root password here
            database=os.getenv('DB_NAME', 'hr_management'),
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except pymysql.Error as e:
        print(f"Error connecting to MySQL: {e}")
        raise
