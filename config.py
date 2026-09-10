import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'simpstock-dev-secret-key-change-in-production')
    JWT_SECRET = os.getenv('JWT_SECRET', 'simpstock-jwt-super-secret-key-change-in-production')
    JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', '24'))

    DATABASE = os.getenv('DATABASE_PATH', os.path.join(BASE_DIR, 'banco.db'))
    if not os.path.isabs(DATABASE):
        DATABASE = os.path.join(BASE_DIR, DATABASE)

    ADMIN_NAME = os.getenv('ADMIN_NAME', 'ADM')
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@simpstock.com')
    ADMIN_DEFAULT_PASSWORD = os.getenv('ADMIN_DEFAULT_PASSWORD', 'admin123')

    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')
