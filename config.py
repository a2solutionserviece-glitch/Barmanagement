import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
    DATABASE_URL = "postgresql://admin:2hFmivuYCP5n8A9V71xMfrOYWxE8sfOT@dpg-d4k4ob0gjchc739uboq0-a/hotelym"

class DevConfig(Config):
    DEBUG = True

class ProdConfig(Config):
    DEBUG = True
