import os
from datetime import datetime, timedelta

import jwt
from dotenv import load_dotenv

load_dotenv()
SECRET = os.getenv("SECRET")


def create_jwt_token(user_info):
    print("SECRET = ", SECRET)
    payload = {
        'id': user_info['id'],
        'username': user_info['username'],
        'role': user_info['role'],
        'exp': datetime.utcnow() + timedelta(minutes=30)  # Токен действует 1 день
    }
    token = jwt.encode(payload, SECRET, algorithm='HS256')
    return token


# Функция для проверки и декодирования JWT токена
def decode_jwt_token(token):
    try:
        payload = jwt.decode(token, SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
