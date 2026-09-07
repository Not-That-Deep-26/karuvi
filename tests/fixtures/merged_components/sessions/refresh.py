# tests/fixtures/merged_components/sessions/refresh.py
import auth.login as login

def refresh_session(token: str):
    return login.do_login()
