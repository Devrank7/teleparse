import os
import secrets
import time
from typing import Optional

from authlib.integrations.requests_client import OAuth2Session
from celery.result import AsyncResult
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, Depends, BackgroundTasks, Query
from fastapi import Request, Form, Response
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.templating import Jinja2Templates

import db
import main1
import my_celery
from auth import auth_backend, jwt_utils
from exception.my_exception import RedirectException

load_dotenv()
app = FastAPI()
templatess = Jinja2Templates(directory="app/templates")

app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_MIDDLEWARE"))
AUTH_URL = 'https://accounts.google.com/o/oauth2/auth'
TOKEN_URL = 'https://oauth2.googleapis.com/token'
USER_INFO_URL = 'https://www.googleapis.com/oauth2/v1/userinfo'
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = 'http://localhost:8000/callback'


def generate_token(data: dict) -> str:
    token = secrets.token_urlsafe(16)
    # Сохранение данных, связанных с токеном (например, в базе данных или в памяти)
    # Здесь используется простой словарь для демонстрации
    tokens[token] = data
    return token


# Получение данных, связанных с токеном
def get_data_from_token(token: str) -> Optional[dict]:
    return tokens.get(token)


# Инициализация словаря токенов
tokens = {}



@app.exception_handler(RedirectException)
async def redirect_exception_handler(request: Request, exc: RedirectException):
    return RedirectResponse(url=exc.headers["Location"])


@app.on_event('startup')
async def startup():
    print('startup')
    await db.init_tables()


@app.get("/")
async def root(request: Request, result=Depends(auth_backend.get_current_user_or_false)):
    if isinstance(result, db.VUser):
        print("username = ", result.username)
    return templatess.TemplateResponse("boot.html", {"request": request, "result": result})


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


@app.get("/goodbye/{name}", response_class=HTMLResponse)
async def good_bye(request: Request, name: str):
    return templatess.TemplateResponse("goodbye.html", {"request": request, "name": name})


@app.get('/login/oauth')
async def login(request: Request, states: str):
    google = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, scope=["profile", "email"])
    authorization_url, state = google.create_authorization_url(AUTH_URL,
                                                               access_type="offline", prompt='consent')
    request.session['oauth_state'] = state
    request.session['states'] = states
    return RedirectResponse(authorization_url)


user_details = {}


@app.get("/callback")
async def callback(request: Request, response: Response):
    google = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI)
    google.fetch_token(TOKEN_URL, client_secret=CLIENT_SECRET, authorization_response=str(request.url))
    user_info = google.get(USER_INFO_URL).json()
    for k, v in user_info.items():
        print(f'{k}: {v}')
    res = request.session.get("states")
    if res == "True":
        # await auth_backend.login(response=response, username=user_info['given_name'], password=user_info['id'])
        token = generate_token({"username": user_info['given_name'], "password": user_info['id']})
        return RedirectResponse(f"/token/oauth?token={token}")
    request.session.pop('states')
    user_details.update({user_info['given_name']: {"password": user_info['id']}})
    print(res)
    return RedirectResponse(f"/number/{user_info['given_name']}")


@app.get("/number/{name}", response_class=HTMLResponse)
async def number(request: Request, name: str):
    return templatess.TemplateResponse("number.html", {"request": request})


@app.post("/number/{name}")
async def number2(response: Response, request: Request, name: str, numbers: str = Form(...)):
    data = user_details.get(name)
    await auth_backend.register(username=name, password=data["password"], number=numbers)
    user_details.pop(name)
    # await db.change_user_number(name=name, number=numbers)
    return RedirectResponse("/login", status_code=303)


@app.get("/login", response_class=HTMLResponse)
async def get_login(request: Request):
    return templatess.TemplateResponse("login.html", {"request": request})


@app.post("/token")
async def login(request: Request, response: Response, username: str = Form(...), password: str = Form(...)):
    response = templatess.TemplateResponse("success.html", {"request": request})
    token = await auth_backend.login(response=response, username=username, password=password)
    if token == "ERROR":
        return RedirectResponse("/", status_code=303)
    print({'access_token': token, 'token_type': 'bearer'})
    return response


@app.get("/token/oauth")
async def logins(request: Request, response: Response, token: str):
    response = templatess.TemplateResponse("success.html", {"request": request})
    data = get_data_from_token(token)
    token_jwt = await auth_backend.login(response=response, username=data['username'], password=data['password'])
    if token_jwt == "ERROR":
        return RedirectResponse("/", status_code=303)
    print({'access_token': token_jwt, 'token_type': 'bearer'})
    return response


@app.get("/register", response_class=HTMLResponse)
async def get_register(request: Request):
    return templatess.TemplateResponse("register.html", {"request": request})


@app.post("/register")
async def register(username: str = Form(...), password: str = Form(...), numbers: str = Form(...)):
    result = await auth_backend.register(username=username, password=password, number=numbers)
    if result == 1:
        print("You have registered yet")
        return RedirectResponse("/login", status_code=303)
    return RedirectResponse("/login", status_code=303)


@app.get("/user", response_class=HTMLResponse)
async def user(request: Request, current_user: db.VUser = Depends(auth_backend.get_current_user)):
    res = await main1.is_authorized_session(number=current_user.number)
    return templatess.TemplateResponse("user.html", {"request": request, "userf": current_user, "res": res})


@app.get("/tg", response_class=HTMLResponse)
async def tg(request: Request, current_user: db.VUser = Depends(auth_backend.get_current_user)):
    res = await main1.logout_session(current_user.number)
    if res:
        return RedirectResponse("/")
    phone_code_hash = await main1.auth_by_number(current_user.number)
    return templatess.TemplateResponse("tg.html",
                                       {"request": request, "code_hash": phone_code_hash, "current_user": current_user})


@app.post("/tg")
async def tg2(code: int = Form(...), code_hash: str = Form(...),
              current_user: db.VUser = Depends(auth_backend.get_current_user)):
    print("code_hash = ", code_hash)
    numbers = current_user.number
    token = generate_token({"code": str(code), "code_hash": code_hash, "numbers": numbers})
    status_code = await main1.authorize_by_name(numbers, code, code_hash)
    match status_code:
        case 0:
            print("OK")
            return RedirectResponse(f"/tg/data", status_code=303)
        case 1:
            print("code 1")
            return RedirectResponse(f"/tg/two/step?token={token}",
                                    status_code=303)
        case 2:
            print("code 2: is invalid")
            return RedirectResponse(f"/tg", status_code=303)
        case 3:
            print("code 3: is invalid")
            return RedirectResponse(f"/tg", status_code=303)


@app.get("/tg/two/step", response_class=HTMLResponse)
async def tg2(request: Request, token: str, current_user: db.VUser = Depends(auth_backend.get_current_user)):
    data = get_data_from_token(token)
    print("code-hash = ", data['code_hash'])
    print("token-hash = ", data['code'])
    return templatess.TemplateResponse("tgp.html", {"request": request, "token": token, "current_user": current_user})


@app.post("/tg/two/step")
async def tg3(token: str = Form(...), password: str = Form(...)):
    data = get_data_from_token(token)
    numbers = data['numbers']
    code = data['code']
    code_hash = data['code_hash']
    print("code-hash = ", code)
    print("token-hash = ", code_hash)
    print("number-hash = ", numbers)

    st_code = await main1.authorize_by_number_with_password(number=numbers, code=int(code), password=password,
                                                            phone_code_hash=code_hash)
    print("st_code = ", st_code)
    if st_code == 1:
        return RedirectResponse(f"/tg/two/step?token={token}", status_code=303)
    return RedirectResponse(f"/tg/data", status_code=303)


@app.post("/logout")
async def logout(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    phone_number = data.get("phone_number")
    print("LOGOUT")
    if phone_number:
        background_tasks.add_task(main1.logout_session, phone_number)
    return {"message": "Logout request received"}


@app.get("/tg/data", response_class=HTMLResponse)
async def tg_data(request: Request, current_user: db.VUser = Depends(auth_backend.get_current_user)):
    data = await main1.get_data_user(number=current_user.number)
    if data == 'Error':
        print("Error")
        print(data['Error'])
        return RedirectResponse(f"/tg", status_code=303)
    return templatess.TemplateResponse("user_data.html",
                                       {"request": request, "name": data['Name'], "number": data['Phone'],
                                        "ID": data['ID']})


@app.get("/tg/all", response_class=HTMLResponse)
async def tg_data_all(request: Request, limit: int = Query(10),
                      current_user: db.VUser = Depends(auth_backend.get_current_user)):
    res = await main1.is_authorized_session(current_user.number)
    if not res:
        return RedirectResponse(f"/tg")
    data = my_celery.get_all_data_async.delay(number=current_user.number, limit=limit)
    print("make")
    return templatess.TemplateResponse("data.html", {"request": request, 'task_id': data.id})


@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    await websocket.accept()
    while True:
        task_result = AsyncResult(task_id)
        if task_result.ready():
            await websocket.send_json({"status": "completed", "data": task_result.result})
            break
        else:
            await websocket.send_json({"status": "loading"})
        time.sleep(1)
    await websocket.close()


@app.get("/tg/logout")
async def logout(request: Request, current_user: db.VUser = Depends(auth_backend.get_current_user)):
    await main1.logout(number=current_user.number)
    return templatess.TemplateResponse("logout.html", {"request": request})


@app.get("/json")
async def json_endpoint(request: Request):
    return {"Name": "Danil", "age": 15}


@app.get("/protect")
async def only_user(request: Request):
    try:
        payload = jwt_utils.decode_jwt_token(request.cookies.get("jwt"))
        if payload["role"] == "user":
            return "You are register"
    except Exception as e:
        print("Error = ", e)
        return "You are not register"


@app.get("/protect/by")
async def protect(current_user: db.VUser = Depends(auth_backend.get_current_user)):
    if current_user.role == "user":
        return "User is protected"
    else:
        return f"You are protected and you are {current_user.role}"


@app.get("/super/protect")
async def super_protect(current_user: db.VUser = Depends(auth_backend.get_current_user)):
    if current_user.role == "admin":
        return "User is protected"
    else:
        return "You are not protected"


@app.get("/get/admin", response_class=HTMLResponse)
async def get_admin(request: Request, current_user: db.VUser = Depends(auth_backend.get_current_user)):
    print("username = ", current_user.username)
    return templatess.TemplateResponse("admin.html", {"request": request})


@app.post("/get/admin")
async def get_admin(password: str = Form(...), current_user: db.VUser = Depends(auth_backend.get_current_user)):
    result = auth_backend.check_password(password=password, hashed_password=current_user.password)
    if result:
        await db.change_user_role(username=current_user.username, role="admin")
        return "You are admin"
    else:
        return "Password is incorrect"

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://34.67.95.102"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
