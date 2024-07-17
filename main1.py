import asyncio
import json
import os

from dotenv import load_dotenv
from telethon import TelegramClient, errors
from telethon.tl import types
from telethon.tl.types import Chat, Channel

load_dotenv()
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")

# Телефонный номер аккаунта Telegram
phone_number = os.getenv("PHONE")


async def authenticate(client):
    try:
        await client.connect()
        if not await client.is_user_authorized():
            await client.send_code_request(phone_number)
            code = input('Please enter the code you received: ')
            await client.sign_in(phone_number, code)
    except errors.SessionPasswordNeededError:
        password = input('Type the password for two step authentication: ')
        await client.sign_in(password=password)
    except errors.PhoneCodeInvalidError:
        print('The code is not correct. Please try again.')
    except errors.PhoneNumberUnoccupiedError:
        print('The number is not register in Telegram.')
    except Exception as e:
        print(f'Error: {e}')
        return False
    return True


async def logout(number):
    client = TelegramClient(f'session_{number}', int(api_id), api_hash)
    await client.connect()
    await client.log_out()
    await client.disconnect()


async def main():
    # Создаем клиент
    client = TelegramClient(session=f'session_{phone_number}', api_id=int(api_id), api_hash=api_hash)
    if await authenticate(client=client):
        try:
            # Получаем текущего пользователя
            me = await client.get_me()
            print(f"Username: {me.username}")
            print(f"Name: {me.first_name} {me.last_name}")
            print(f"Phone: {me.phone}")

            # Получаем список диалогов (чатов, групп, каналов)
            dialogs = await client.get_dialogs()

            for dialog in dialogs:
                print(f"Title: {dialog.title}")
                print(f"ID: {dialog.id}")
                print(f"Type: {type(dialog.entity).__name__}")
        except Exception as e:
            print(f"Error when you get the data: {e}")
    else:
        print('do not try appeal your number.')
    if client.is_connected():
        print("Disconnect client...")
        # await client.log_out()
        await client.disconnect()
        print("The client has been disconnected successfully.")
    else:
        print("The has been disconnected yet.")


async def auth_by_number(number):
    client = TelegramClient(session=f'session_{number}', api_id=int(api_id), api_hash=api_hash)
    await client.connect()
    try:
        if not await client.is_user_authorized():
            result = await client.send_code_request(number)
            phone_code_hash = result.phone_code_hash
            return phone_code_hash
        else:
            return None
    finally:
        await client.disconnect()


async def authorize_by_name(number, code, phone_code_hash):
    client = TelegramClient(session=f'session_{number}', api_id=int(api_id), api_hash=api_hash)
    await client.connect()
    try:
        if not await client.is_user_authorized():
            try:
                await client.sign_in(phone=number, code=code, phone_code_hash=phone_code_hash)
                return 0
            except errors.SessionPasswordNeededError:
                return 1
            except errors.PhoneCodeInvalidError:
                return 2
            except errors.PhoneNumberUnoccupiedError:
                return 3
        else:
            return -1
    finally:
        await client.disconnect()


async def authorize_by_number_with_password(number, code, phone_code_hash, password):
    client = TelegramClient(session=f'session_{number}', api_id=int(api_id), api_hash=api_hash)
    await client.connect()
    try:
        if not await client.is_user_authorized():
            try:
                await client.sign_in(phone=number, code=int(code), phone_code_hash=phone_code_hash)
            except errors.SessionPasswordNeededError:
                try:
                    await client.sign_in(password=password)
                    return 0
                except errors.PasswordHashInvalidError:
                    print("The password is incorrect. Please try again.")
                    return 1
            except Exception as e:
                print(f"Error : ")
                return 1
    finally:
        await client.disconnect()


async def get_data_user(number):
    client = TelegramClient(session=f'session_{number}', api_id=int(api_id), api_hash=api_hash)
    await client.connect()
    try:
        if await client.is_user_authorized():
            my = await client.get_me()
            print(f"Username: {my.username}")
            print(f"Name: {my.first_name} {my.last_name}")
            print(f"Phone: {my.phone}")
            return {"Name": my.username, "Phone": my.phone, "ID": my.id}
        else:
            await client.log_out()
    finally:
        await client.disconnect()
    return "Error"


async def get_data_all(number, limit):
    client = TelegramClient(session=f'session_{number}', api_id=int(api_id), api_hash=api_hash)
    await client.connect()
    try:
        if await client.is_user_authorized():
            my = await client.get_me()
            print(f"Username: {my.username}")
            print(f"Name: {my.first_name} {my.last_name}")
            print(f"Phone: {my.phone}")
            dump_data = {"Username": my.username, "Phone": my.phone, "id": my.id, "first_name": my.first_name,
                         "last_name": my.last_name}
            chats = []
            dialogs = await client.get_dialogs()
            for dialog in dialogs:
                if isinstance(dialog.entity, types.User):
                    # Личная переписка
                    print(
                        f"Chat link: https://t.me/{dialog.entity.username if dialog.entity.username else dialog.entity.id}")
                    link = f"https://t.me/{dialog.entity.username if dialog.entity.username else dialog.entity.id}"
                elif isinstance(dialog.entity, (Chat, Channel)):
                    # Группы и каналы
                    if hasattr(dialog.entity, 'username') and dialog.entity.username:
                        print(f"Chat link: https://t.me/{dialog.entity.username}")
                        link = f'https://t.me/{dialog.entity.username}'
                    else:
                        print(f"Chat link: (No public link available)")
                        link = 'No public link available'
                else:
                    link = 'not found link'
                m = []
                async for message in client.iter_messages(dialog.id, limit=limit):
                    m.append({message.id: message.text})
                d = {dialog.title: {"id": dialog.id, "link": link, "messages": m}}
                chats.append(d)
            dump_data.update({"chats": chats})
            with open(f"data{number}.json", "w", encoding="utf-8") as file:
                json.dump(dump_data, file, indent=4, ensure_ascii=False)
            return dump_data
        else:
            await client.log_out()
            return {"Error": "You are not authorized."}
    finally:
        await client.disconnect()


sessions_dir = os.path.dirname(os.path.abspath(__file__))


async def check_session(session_name):
    client = TelegramClient(session_name, int(api_id), api_hash)
    try:
        await client.connect()
        if await client.is_user_authorized():
            print(f'Session {session_name} is active.')
            return True
        else:
            print(f'Session {session_name} exists but is not authorized.')
            await client.log_out()
            return False
    except Exception as e:
        print(f'Error checking session {session_name}: {e}')
        return False
    finally:
        await client.disconnect()


async def logout_session(number):
    session_files = [f for f in os.listdir(sessions_dir) if f.endswith('.session') and number in f]
    for session_file in session_files:
        session_name = os.path.join(sessions_dir, session_file)
        print("Session " + session_name)
        return await check_session(session_name)


async def is_authorized_session(number: str):
    res = await check_session("session_" + str(number))
    return res


if __name__ == "__main__":
    asyncio.run(main())
