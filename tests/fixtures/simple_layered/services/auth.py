# tests/fixtures/simple_layered/services/auth.py
from repositories.users import UserRepository

repo = UserRepository()

def authenticate(user_id: int):
    user = repo.find_by_id(user_id)
    return user is not None
