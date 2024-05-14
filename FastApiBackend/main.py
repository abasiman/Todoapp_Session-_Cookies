from fastapi import HTTPException, Depends, FastAPI
from typing import Annotated, List
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import SessionLocal, engine, Base
from models import TodoList, CompletedList
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware


from fastapi.responses import JSONResponse
from jose import jwt
import requests
from typing import Annotated
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Users, RefreshToken
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from datetime import datetime, timedelta
from jose import jwt, JWTError
from typing import Optional
import logging
from sqlalchemy.exc import SQLAlchemyError
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel

from fastapi import Cookie, HTTPException
from fastapi import HTTPException, Depends, FastAPI, APIRouter, Cookie, Response, status
from typing import Optional
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Users, RefreshToken
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime, timedelta


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173",
                   "https://todolist-application-9jvne2ayx-abas-imans-projects.vercel.app"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# create pydantic models

router = APIRouter(


    prefix="/auth",
    tags=["auth"]

)


# pydantic models
class CreateUserRequest(BaseModel):

    username: str
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    username: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependecy = Annotated[Session, Depends(get_db)]


logger = logging.getLogger(__name__)
SECRET_KEY = '194679e3j938492938382883dej3ioms998323ftu933@jd7233!'
ALGORITHM = 'HS256'

bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


# Register endpoint
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependecy, create_user_request: CreateUserRequest):
    try:
        create_user_model = Users(
            username=create_user_request.username,
            email=create_user_request.email,
            hashed_password=bcrypt_context.hash(create_user_request.password),
        )
        db.add(create_user_model)
        db.commit()

    except SQLAlchemyError as e:
        logger.error(f"Error creating user: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create user")
    except Exception as e:
        logger.error(f"Unexpected error creating user: {e}")
        raise HTTPException(status_code=500, detail="Unexpected error")


# This function generates a refresh token,
# which is used to obtain a new access token without requiring the user to log in again.
# For example, when the user session expires it regenrates the token

def create_refresh_token(user_id: int, expires_delta: Optional[timedelta] = None):
    encode = {'id': user_id}
    if expires_delta:
        expires = datetime.utcnow() + expires_delta
        encode.update({'exp': expires})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)


# The following endpoint refreshes the access token using a provided refresh token
# Allows users to obtain a new access token without having to log in again,
#  extending user sessions and maintaining access to protected resources over time. now set to 24 hrs
@router.post("/refresh", response_model=Token)
async def refresh_access_token(refresh_token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("id")
        if user_id is None:
            raise HTTPException(
                status_code=401, detail="Invalid refresh token")

        # Validate refresh token in the database
        db_token = db.query(RefreshToken).filter(
            RefreshToken.token == refresh_token, RefreshToken.user_id == user_id).first()
        if not db_token or db_token.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=401, detail="Refresh token expired")

        user = db.query(Users).filter(Users.id == user_id).first()
        new_access_token = create_user_token(
            user.username, user.email, user.id, timedelta(hours=24))

        return {"access_token": new_access_token, "token_type": "bearer"}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    try:
        user = authenticate_user(form_data.username, form_data.password, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail='Incorrect email or password')

        # Generate access token and session token
        access_token = create_user_token(
            username=user.username,
            email=user.email,
            user_id=user.id,
            expires_delta=timedelta(hours=24)
        )
        refresh_token = create_refresh_token(user.id, timedelta(days=7))
        new_refresh_token = RefreshToken(
            token=refresh_token, user_id=user.id, expires_at=datetime.utcnow() +
            timedelta(days=7)
        )
        db.add(new_refresh_token)
        db.commit()

        # Set session token as cookie
        # response = {"access_token": access_token,
        # "token_type": "bearer", "username": user.username}
        # response.set_cookie(key="session_token", value=access_token,
        # httponly=True, secure=True)

        response = Response(content={
                            "access_token": access_token, "token_type": "bearer", "username": user.username})
        response.set_cookie(key="session_token",
                            value=access_token, httponly=True, secure=True)

        return response
    except Exception as e:
        logger.error(f"Unexpected error during login: {e}")
        raise HTTPException(
            status_code=500, detail="Unexpected error during login")

# Middleware for session validation


async def session_middleware(session_token: str = Cookie(None)):
    try:
        payload = jwt.decode(session_token, SECRET_KEY, algorithms=[ALGORITHM])
        # Validate session token here (e.g., check expiry)
        # Optionally, decode user information from the session token for use in subsequent requests
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid session token")

# Apply middleware globally
app.add_middleware(SessionMiddleware, session_middleware)


# This function verifies user credentials during the login process.
def authenticate_user(email: str, password: str, db):

    user = db.query(Users).filter(Users.email == email).first()
    if bcrypt_context.verify(password, user.hashed_password):
        return user
    return None


def create_user_token(username: str, email: str, user_id: int, expires_delta: Optional[timedelta] = None):
    encode = {'sub': username, 'email': email, 'id': user_id}
    if expires_delta:
        expires = datetime.utcnow() + expires_delta
        encode.update({'exp': expires})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)


class TodoBase(BaseModel):
    newItem: str


class TodoModel(TodoBase):
    id: int

    class Config:
        orm_mode = True

# database dependencies


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


#  tables in the database
Base.metadata.create_all(bind=engine)

# endpoints


@app.post("/TodoList/", response_model=TodoModel)
async def create_todos(todo: TodoBase,  db: Session = Depends(get_db)):
    db_todo = TodoList(newItem=todo.newItem)
    db.add(db_todo)
    db.commit()
    db.refresh(db_todo)
    return db_todo


@app.get("/TodoList/", response_model=List[TodoModel])
async def get_todos(db: Session = Depends(get_db)):
    return db.query(TodoList).all()


@app.delete("/TodoList/{todo_id}/", response_model=TodoModel)
async def delete_todo(todo_id: int, db: Session = Depends(get_db)):
    db_todo = db.query(TodoList).filter(TodoList.id == todo_id).first()
    if db_todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    db.delete(db_todo)
    db.commit()
    return db_todo


@app.put("/TodoList/{todo_id}/", response_model=TodoModel)
async def update_todo(todo_id: int, todo: TodoBase, db: Session = Depends(get_db)):
    db_todo = db.query(TodoList).filter(TodoList.id == todo_id).first()
    if db_todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    db_todo.newItem = todo.newItem
    db.commit()
    db.refresh(db_todo)
    return db_todo


# Clear All Todolist
@app.delete("/TodoList/", response_model=None)
async def clear_todo_list(db: Session = Depends(get_db)):
    try:
        db.query(TodoList).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# completed list
class CompletedBase(BaseModel):
    completedItem: str


class CompletedModel(CompletedBase):
    id: int

    class Config:
        orm_mode = True


@app.post("/CompletedList/", response_model=CompletedModel)
async def create_completed(completed: CompletedBase,  db: Session = Depends(get_db)):
    db_completed = CompletedList(completedItem=completed.completedItem)
    db.add(db_completed)
    db.commit()
    db.refresh(db_completed)
    return db_completed


@app.get("/CompletedList/", response_model=List[CompletedModel])
async def get_completed(db: Session = Depends(get_db)):
    return db.query(CompletedList).all()


# clear all the completed tasks
@app.delete("/CompletedList/", response_model=None)
async def clear_completed_list(db: Session = Depends(get_db)):
    try:
        db.query(CompletedList).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
