import os

class Config:
    # MySQL Configuration
    # You (the user) must update these values if your database settings are different.
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'       # Default MySQL user
    MYSQL_PASSWORD = 'root'       # Default empty password (common for XAMPP/WAMP or fresh installs). CHANGE THIS if you have a password!
    MYSQL_DB = 'box_cricket_db'

    # Security
    SECRET_KEY = 'dev-secret-key-change-in-production'

    # Notification Credentials (Env vars preferred, fallbacks here)
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    
    
    TWILIO_SID = os.environ.get('TWILIO_SID')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
    TWILIO_WHATSAPP_NUM = os.environ.get('TWILIO_WHATSAPP_NUM')
    ADMIN_PHONE = os.environ.get('ADMIN_PHONE')
