# tests/fixtures/simple_layered/api/main.py
from services.auth import authenticate
from services.users import get_profile

def handle_request(user_id: int):
    if authenticate(user_id):
        return get_profile(user_id)
    return None
