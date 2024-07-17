from functools import wraps

import bcrypt
from fastapi import Response, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from starlette import status
from starlette.responses import RedirectResponse

import db
from auth import jwt_utils
from exception import my_exception

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_current_user(request: Request):
    # credentials_exception = HTTPException(
    #     status_code=status.HTTP_401_UNAUTHORIZED,
    #     detail="Could not validate credentials",
    #     headers={"WWW-Authenticate": "Bearer"},
    # )
    token = request.cookies.get("jwt")
    if token is None:
        raise my_exception.RedirectException("/login")
    print("token", token)
    payload = jwt_utils.decode_jwt_token(token)
    print("payload", payload)
    user = await db.get_user_by_username(payload['username'])
    if user is None:
        raise my_exception.RedirectException("/login")
    return user


async def get_current_user_gpt(request: Request):
    token = request.cookies.get("jwt")
    if token is None:
        return None  # Возвращаем None вместо редиректа
    print("token", token)
    try:
        payload = jwt_utils.decode_jwt_token(token)
        print("payload", payload)
        user = await db.get_user_by_username(payload['username'])
        if user is None:
            return None  # Возвращаем None вместо редиректа
        return user
    except Exception as e:
        return None  # Возвращаем None вместо редиректа


def login_required(func):
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        current_user = await get_current_user(request)
        if current_user is None:
            return RedirectResponse("/login", status_code=303)
        kwargs['current_user'] = current_user
        return await func(request, *args, **kwargs)
    return wrapper


async def get_current_user_or_false(request: Request):
    try:
        token = request.cookies.get("jwt")
        payload = jwt_utils.decode_jwt_token(token)
        print("payload", payload)
        user = await db.get_user_by_username(payload['username'])
        if user is None:
            return False
        return user
    except Exception as e:
        print("Error = ", e)
        return False


async def register(username, password, number, role='user'):
    user_test = await db.get_user_by_username(username)
    if user_test is not None:
        return 1
    hash_pass = hash_password(password=password)
    user = await db.create_user(name=username, password=hash_pass, number=number, role=role)
    print("The user '{}' has been registered.".format(username))
    return user


async def login(response: Response, username, password):
    print("l-1")
    user = await db.get_user_by_username(username)
    print("l0")
    if user is None or not check_password(password, user.password):
        return "ERROR"
    print("l1")
    token = jwt_utils.create_jwt_token({"username": username, "id": user.id, "role": user.role})
    response.set_cookie(key="jwt", value=token, httponly=True, max_age=1800)
    print("l2")
    return token


def hash_password(password: str) -> str:
    # Преобразуем пароль в байты и создаем соль
    salt = bcrypt.gensalt()
    # Хешируем пароль
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')


# Функция для проверки пароля
def check_password(password: str, hashed_password: str) -> bool:
    # Преобразуем оба значения в байты и проверяем пароль
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
