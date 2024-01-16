from typing import Type

from sqlalchemy import Column, Integer, String, insert, select
from sqlalchemy.orm import declarative_base, sessionmaker  # type: ignore

Base = declarative_base()


class Greeting(Base):
    __tablename__ = "greetings"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(String)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

    @classmethod
    async def get_users(cls: Type['User'], session_maker: sessionmaker, username):
        async with session_maker() as session:
            sql = select(cls).where(cls.username == username)
            result = await session.execute(sql)
            user: cls = result.scalar()
        return user

    @classmethod
    async def insert_user(
        cls: Type['User'], session_maker: sessionmaker, username: str, hashed_password: str
    ):
        async with session_maker() as session:
            sql = insert(cls).values(username=username,
                                     hashed_password=hashed_password)
            await session.execute(sql)
            await session.commit()
