from sqlalchemy import Column, Integer, String

from app.db import Base


class Greeting(Base):
    __tablename__ = "greetings"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(String)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
