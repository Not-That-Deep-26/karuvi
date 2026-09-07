# tests/fixtures/merged_components/auth/login.py
import sessions.token as token

def do_login():
    return token.make_token()
