import os
import psycopg2
from flask import g
from config import Config

def get_db():
    if "db" not in g:
        g.db = psycopg2.connect(Config.DATABASE_URL)
    return g.db

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
