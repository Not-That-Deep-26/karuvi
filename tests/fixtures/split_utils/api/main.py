# tests/fixtures/split_utils/api/main.py
from utils.auth import check_login

def run():
    return check_login()
