# tests/fixtures/simple_layered/services/users.py
from repositories.users import UserRepository

repo = UserRepository()

def get_profile(user_id: int):
    return repo.find_by_id(user_id)
