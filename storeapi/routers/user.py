import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, status, Request, BackgroundTasks, Depends
from fastapi.security import OAuth2PasswordRequestForm

from storeapi.database import database, user_table
from storeapi.models.user import UserIn
from storeapi.security import (
    get_user,
    get_subject_for_token_type,
    get_password_hash,
    authenticate_user,
    create_access_token,
    create_confirmation_token
)
from storeapi import tasks

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user: UserIn, request: Request, background_tasks: BackgroundTasks):
    if await get_user(user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    hashed_password = get_password_hash(user.password)
    query = user_table.insert().values(email=user.email, password=hashed_password)
    logger.debug(query)

    await database.execute(query)
    background_tasks.add_task(
        tasks.send_user_registration_email,
        user.email,
        confirmation_url=request.url_for(
            "confirm_email", token=create_confirmation_token(user.email)
        ),
    )
    return {"detail": "User created successfully. Please confirm your email."}


@router.post("/token_user")
async def login_user(user: UserIn):
    user = await authenticate_user(user.email, user.password)
    access_token = create_access_token(user.email)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/token")
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = await authenticate_user(form_data.username, form_data.password)
    access_token = create_access_token(user.email)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/confirm/{token}")
async def confirm_email(token: str):
    email = get_subject_for_token_type(token, "confirmation")
    query = user_table.update().where(user_table.c.email == email).values(confirmed=True)
    logger.debug(query)

    await database.execute(query)
    return {"detail": "Email confirmed successfully"}
