# tests/fixtures/split_utils/utils/auth.py
from utils.database import DB

db = DB()

def check_login():
    return db.query() is not None
