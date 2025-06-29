import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Azure SQL Konfiguration
    SQL_SERVER = os.getenv('SQL_SERVER')
    SQL_DATABASE = os.getenv('SQL_DATABASE')
    SQL_USERNAME = os.getenv('SQL_USERNAME')
    SQL_PASSWORD = os.getenv('SQL_PASSWORD')
    SQL_DRIVER = '{ODBC Driver 17 for SQL Server}'
    
    # Verbindungsstring
    SQLALCHEMY_DATABASE_URI = f"mssql+pyodbc://{SQL_USERNAME}:{SQL_PASSWORD}@{SQL_SERVER}/{SQL_DATABASE}?driver={SQL_DRIVER}"
    
    # Sicherheit
    SECRET_KEY = os.getenv('SECRET_KEY') or 'ein-sehr-langer-geheimer-schluessel-min-32-zeichen'
    
    # Azure AD Konfiguration (einfache Version)
    AZURE_AD_TENANT = os.getenv('AZURE_AD_TENANT')