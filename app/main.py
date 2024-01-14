import datetime
from typing import List, Type

import aioredis
import dotenv
import uvicorn
from fastapi import Depends, FastAPI, Form, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

dotenv.load_dotenv()

from sqlalchemy.orm import Session  # noqa: E402

from app import models, schemas  # noqa: E402
from app.db import SessionLocal, engine  # noqa: E402
from app.models import User  # noqa: E402
from app.schemas import Greeting  # noqa: E402
from app.settings import settings  # noqa: E402


class LazyDbInit:
    is_initialized = False

    @classmethod
    def initialize(cls):
        if not cls.is_initialized:
            models.Base.metadata.create_all(bind=engine)
            cls.is_initialized = True


server = FastAPI()


def get_db() -> Session:
    LazyDbInit.initialize()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(data: dict, expires_delta: datetime.timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt


def create_user(db: Session, username: str, password: str):
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        raise ValueError("User with this username already exists")

    db_user = User(username=username, hashed_password=password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    db.close()
    if user is None:
        raise credentials_exception
    return user


@server.post("/token")
async def login_for_access_token(
    username: str = Form(...), password: str = Form(...)
) -> dict:
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    db.close()
    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = datetime.timedelta(
        minutes=int(settings.access_token_expire_minutes)
    )
    access_token = create_access_token(
        data={"sub": username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


@server.post("/register")
async def register(username: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    try:
        hashed_password = hash_password(password)
        create_user(db, username, hashed_password)
        return {"username": username}
    finally:
        db.close()


@server.get("/", response_model=List[schemas.Greeting])
async def root(db: Session = Depends(get_db)) -> List[Type[schemas.Greeting]]:
    text = str(datetime.datetime.now())
    greeting = Greeting(text=text)
    db_greeting = models.Greeting(**greeting.dict())
    db.add(db_greeting)
    db.commit()
    return db.query(models.Greeting).all()


@server.get("/hello")
async def hello() -> dict:
    return {"hello": "world"}


if __name__ == "__main__":
    uvicorn.run(server, host="0.0.0.0", port=8001)
