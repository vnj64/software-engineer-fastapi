import datetime
import time
from typing import List, Type
import dotenv
import uvicorn
from fastapi_redis import Redis
from fastapi import Depends, FastAPI, Form, HTTPException, status, Response, Request 
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
import aioredis

dotenv.load_dotenv()

from sqlalchemy.orm import Session  # noqa: E402

from app import models, schemas  # noqa: E402
from app.db import SessionLocal, engine  # noqa: E402
from app.models import User  # noqa: E402
from app.schemas import Greeting  # noqa: E402
from app.settings import settings  # noqa: E402

from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST


class LazyDbInit:
    is_initialized = False

    @classmethod
    def initialize(cls):
        if not cls.is_initialized:
            models.Base.metadata.create_all(bind=engine)
            cls.is_initialized = True


server = FastAPI()

request_counter_by_path = Counter('requests_total', 'Total number of requests', ['path'])
error_counter_by_path = Counter('errors_total', 'Total number of errors', ['path'])
execution_time_by_path = Histogram('execution_time_seconds', 'Execution time of each endpoint', ['path'])
integration_execution_time = Histogram('integration_execution_time_seconds', 'Execution time of integration methods')


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


def get_db() -> Session:
    LazyDbInit.initialize()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
    request_counter.labels(path).inc()
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
    username: str = Form(...),
    password: str = Form(...),
    redis: Redis = Depends(get_redis),
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

    access_token_expires = datetime.timedelta(minutes=int(settings.access_token_expire_minutes))
    access_token = create_access_token(data={"sub": username}, expires_delta=access_token_expires)

    await redis.set(username, access_token)

    return {"access_token": access_token, "token_type": "bearer"}


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


@server.post("/register")
async def register(username: str = Form(...), password: str = Form(...), redis: aioredis.Redis = Depends(get_redis_dependency)):
    db = SessionLocal()
    try:
        hashed_password = hash_password(password)
        create_user(db, username, hashed_password)

        registration_timestamp = datetime.datetime.utcnow().timestamp()
        await redis.set(f"{username}_registration_timestamp", str(registration_timestamp))

        return {"username": username}
    finally:
        db.close()


@server.get("/")
async def root(db: Session = Depends(get_db), redis: Redis = Depends(get_redis_dependency)) -> List[schemas.Greeting]:
    path = "/"

    with integration_execution_time.time():
        text = str(datetime.datetime.now())
        greeting = Greeting(text=text)
        db_greeting = models.Greeting(**greeting.dict())
        db.add(db_greeting)
        db.commit()

    return db.query(models.Greeting).all()


@server.get("/hello")
async def hello() -> dict:
    return {"hello": "world"}


@server.get("/metrics")
async def get_metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

if __name__ == "__main__":
    uvicorn.run(server, host="0.0.0.0", port=8001)
