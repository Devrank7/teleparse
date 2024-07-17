from sqlalchemy import BigInteger, String, Select, Boolean
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

engine = create_async_engine(url='postgresql+asyncpg://postgres:boot@localhost:7432/stream_sql', echo=True)
session_as = async_sessionmaker(engine)


class Base(DeclarativeBase, AsyncAttrs):
    pass


class VUser(Base):
    __tablename__ = 'vuser'
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String, unique=True)
    number: Mapped[str] = mapped_column(String)
    password: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default='user')


async def get_db():
    async with session_as() as session:
        yield session


async def init_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_user(idd: int):
    async with session_as() as ses:
        return await ses.scalar(Select(VUser).where(VUser.id == idd))


async def get_user_by_username(username: str):
    async with session_as() as ses:
        return await ses.scalar(Select(VUser).where(VUser.username == username))


async def create_user(name: str, number: str, password: str, role: str):
    async with session_as() as ses:
        rec = VUser()
        rec.username = str(name)
        rec.number = str(number)
        rec.password = str(password)
        rec.role = role
        ses.add(rec)
        await ses.commit()


async def change_user_number(name: str, number: str):
    async with session_as() as ses:
        user = await ses.scalar(Select(VUser).where(VUser.name == name))
        user.number = str(number)
        await ses.commit()


async def change_user_role(username: str, role: str):
    async with session_as() as ses:
        user = await ses.scalar(Select(VUser).where(VUser.username == username))
        user.role = str(role)
        await ses.commit()
