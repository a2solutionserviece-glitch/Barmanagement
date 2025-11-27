import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
    DATABASE_URL = os.getenv("DATABASE_URL")

class DevConfig(Config):
    DEBUG = True

class ProdConfig(Config):
    DEBUG = False
