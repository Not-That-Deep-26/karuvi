# tests/fixtures/merged_components/sessions/token.py
import sessions.refresh as refresh

def make_token():
    return refresh.refresh_session("abc")
