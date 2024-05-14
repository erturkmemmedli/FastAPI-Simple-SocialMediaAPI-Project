import pytest
from fastapi import HTTPException
from jose import jwt
from pytest_mock import MockerFixture

from storeapi.security import (
    get_user,
    get_password_hash,
    verify_password,
    get_subject_for_token_type,
    access_token_expires_minute,
    confirm_token_expires_minute,
    create_confirmation_token,
    create_access_token,
    authenticate_user,
    get_current_user,
    SECRET_KEY,
    ALGORITHM
)


def test_access_token_expires_minute():
    assert access_token_expires_minute() == 30


def test_confirm_token_expires_minute():
    assert confirm_token_expires_minute() == 1440


def test_create_access_token():
    token = create_access_token('a@b2.com')
    assert {'sub': 'a@b2.com', 'type': 'access'}.items() <= jwt.decode(
        token, key=SECRET_KEY, algorithms=[ALGORITHM]
    ).items()


def test_create_confirmation_token():
    token = create_confirmation_token('a@b2.com')
    assert {'sub': 'a@b2.com', 'type': 'confirmation'}.items() <= jwt.decode(
        token, key=SECRET_KEY, algorithms=[ALGORITHM]
    ).items()


def test_get_subject_for_token_type_valid_confirmation():
    email = 'a@b2.com'
    token = create_confirmation_token(email)

    assert email == get_subject_for_token_type(token, "confirmation")


def test_get_subject_for_token_type_valid_access():
    email = 'a@b2.com'
    token = create_access_token(email)

    assert email == get_subject_for_token_type(token, "access")


def test_get_subject_for_token_type_expired(mocker: MockerFixture):
    mocker.patch('storeapi.security.access_token_expires_minute', return_value=-1)
    email = 'a@b2.com'
    token = create_access_token(email)

    with pytest.raises(HTTPException) as exc_info:
        get_subject_for_token_type(token, "access")

    assert exc_info.value.detail == "Token has expired"


def test_get_subject_for_token_type_invalid_token():
    token = 'invalid token'

    with pytest.raises(HTTPException) as exc_info:
        get_subject_for_token_type(token, "access")

    assert exc_info.value.detail == "Invalid token"


def test_get_subject_for_token_type_missing_sub():
    email = 'a@b2.com'
    token = create_access_token(email)
    payload = jwt.decode(token, key=SECRET_KEY, algorithms=[ALGORITHM])
    del payload['sub']
    token = jwt.encode(payload, key=SECRET_KEY, algorithm=ALGORITHM)

    with pytest.raises(HTTPException) as exc_info:
        get_subject_for_token_type(token, "access")

    assert exc_info.value.detail == "Token is missing 'sub' field"


def test_get_subject_for_token_type_wrong_type():
    email = 'a@b2.com'
    token = create_confirmation_token(email)

    with pytest.raises(HTTPException) as exc_info:
        get_subject_for_token_type(token, "access")

    assert 'Token has incorrect type' in exc_info.value.detail


def test_password_hashing():
    password = "password"

    assert verify_password(password, get_password_hash(password))


@pytest.mark.anyio
async def test_get_user(registered_user: dict):
    user = await get_user(registered_user['email'])

    assert user.email == registered_user['email']


@pytest.mark.anyio
async def test_get_user_not_found():
    user = await get_user('test@example.com')

    assert user is None


@pytest.mark.anyio
async def test_authenticate_user(confirmed_user: dict):
    user = await authenticate_user(confirmed_user['email'], confirmed_user['password'])

    assert user.email == confirmed_user['email']


@pytest.mark.anyio
async def test_authenticate_user_not_found():
    with pytest.raises(HTTPException):
        await authenticate_user("test@example.com", "1234")


@pytest.mark.anyio
async def test_authenticate_user_wrong_password(registered_user: dict):
    with pytest.raises(HTTPException):
        await authenticate_user(registered_user['email'], "wrong password")


@pytest.mark.anyio
async def test_get_current_user(registered_user: dict):
    token = create_access_token(registered_user['email'])
    user = await get_current_user(token)

    assert user.email == registered_user['email']


@pytest.mark.anyio
async def test_get_current_user_invalid_token():
    with pytest.raises(HTTPException):
        await get_current_user('invalid token')


@pytest.mark.anyio
async def test_get_current_user_wrong_type_token(registered_user: dict):
    token = create_confirmation_token(registered_user['email'])

    with pytest.raises(HTTPException):
        await get_current_user(token)
