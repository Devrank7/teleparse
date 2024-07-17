import uuid

from fastapi import Depends
from fastapi_users import schemas, FastAPIUsers, models
from fastapi_users.authentication import AuthenticationBackend, CookieTransport
from fastapi_users.authentication import JWTStrategy
from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users.manager import BaseUserManager, UUIDIDMixin
from fastapi_users.schemas import BaseUser, BaseUserCreate, BaseUserUpdate

import db

SECRET = "d7a0e1c0c7h1492w6d91f6e7e9189f5f3q0e8a6b3a2d0e4e8f7a6d0e4e8f7a6d"  # Замените на ваш секретный ключ


class User(BaseUser):
    pass


class UserCreate(BaseUserCreate):
    pass


class UserUpdate(User, BaseUserUpdate):
    pass


class UserDB(User, BaseUserDB):
    pass


user_db = SQLAlchemyUserDatabase(UserDB, db.session_as(), User)

cookie_transport = CookieTransport(cookie_max_age=3600)


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600)


auth_backend = JWTStrategy(name="jwt", transport=cookie_transport, get_strategy=get_jwt_strategy)

fastapi_users = FastAPIUsers(
    user_db,
    [auth_backend],
    User,
    UserCreate,
    UserUpdate,
    UserDB,
)
