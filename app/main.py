import datetime
import logging
import time
from typing import Any, Dict

import aioredis
import dotenv
import uvicorn
from asyncpg import UniqueViolationError
from fastapi import (Depends, FastAPI, Form, HTTPException, Request, Response,
                     status)
from fastapi.security import OAuth2PasswordBearer
from fastapi_redis import Redis  # type: ignore
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

dotenv.load_dotenv()

import sentry_sdk  # noqa: E402
from prometheus_client import Counter  # noqa: E402
from prometheus_client import Histogram  # noqa: E402
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app import models  # noqa: E402
from app.db import create_db_session  # noqa: E402
from app.models import User  # noqa: E402
from app.settings import settings  # noqa: E402

sentry_sdk.init(
    dsn=settings.sentry_url,
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
)

server = FastAPI()

request_counter_by_path = Counter(
    "requests_total", "Total number of requests", ["path"]
)
error_counter_by_path = Counter("errors_total", "Total number of errors", ["path"])

execution_time_by_path = Histogram(
    "execution_time_seconds", "Execution time of each endpoint", ["path"]
)

integration_execution_time = Histogram(
    "integration_execution_time_seconds", "Execution time of integration methods"
)

logging.basicConfig(
    level=logging.INFO,
    filename=f"app/log/{__name__}.log",
    filemode="w+",
    format="%(asctime)s %(levelname)s %(message)s",
)


class LazyDbInit:
    is_initialized = False

    @classmethod
    async def initialize(cls):
        if not cls.is_initialized:
            async with create_db_session() as session:
                result = await session.execute(
                    select(models.Base.metadata.tables.values())
                )
                tables = result.scalars().all()
                if not tables:
                    models.Base.metadata.create_all(bind=create_async_engine())
                    cls.is_initialized = True


@server.get("/sentry-debug")
async def trigger_error():
    division_by_zero = 1 / 0
    print(division_by_zero)


@server.middleware("http")
async def start_timer(request: Request, call_next):
    request.state.start_time = time.time()
    response = await call_next(request)
    return response


@server.middleware("http")
async def add_metrics(request: Request, call_next):
    path = request.url.path

    request_counter_by_path.labels(path=path).inc()

    try:
        response = await call_next(request)
    except Exception as e:
        error_counter_by_path.labels(path=path).inc()
        raise e

    execution_time = time.time() - request.state.start_time
    execution_time_by_path.labels(path=path).observe(execution_time)

    return response


async def get_redis():
    redis = await aioredis.from_url(settings.redis_url)
    try:
        yield redis
    finally:
        await redis.close()


async def get_redis_dependency(redis: aioredis.Redis = Depends(get_redis)):
    try:
        yield redis
    finally:
        await redis.close()


async def get_metrics_dependency(request: Request):
    path = request.url.path
    request_counter_by_path.labels(path).inc()
    yield


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


@server.post("/token")
async def login_for_access_token(
    username: str = Form(...),
    password: str = Form(...),
    redis: Redis = Depends(get_redis),
) -> Dict[str, Any]:
    session = await create_db_session()

    result = await User.get_users(session, username=username)
    user = result

    if not user or not user.hashed_password:
        logging.info(f"Пользователь {user} не авторизован")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(password, str(user.hashed_password)):
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

    await redis.set(username, access_token)
    logging.info(f"Пользователь {username} успешно получил свой токен.")
    return {"access_token": access_token, "token_type": "bearer"}


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


@server.post("/register")
async def register(
    username: str = Form(...),
    password: str = Form(...),
    redis: aioredis.Redis = Depends(get_redis_dependency),
):
    session = await create_db_session()
    try:
        hashed_password = hash_password(password)
        await User.insert_user(
            session_maker=session, username=username, hashed_password=hashed_password
        )

        registration_timestamp = datetime.datetime.utcnow().timestamp()
        await redis.set(
            f"{username}_registration_timestamp", str(registration_timestamp)
        )
        logging.info(f"Пользователь с именем {username} успешно создан. 200.")
        return {"username": username}
    except UniqueViolationError as e:
        logging.error(e)
        raise HTTPException(status_code=404, detail="Такой пользователь существует.")


@server.get("/")
async def hello() -> dict:
    return {"hello": "world"}


@server.get("/metrics")
async def get_metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    uvicorn.run(server, host="0.0.0.0", port=8001)
