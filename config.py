import os


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'f3653358896fc6e16a78ada0dcde63dc67cfd4c3172e381ae373ddaff32e9b06')
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'mysql+pymysql://root:chin1987@localhost:3306/criminology'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
