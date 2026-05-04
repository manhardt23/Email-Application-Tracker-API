from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_db
from app.auth.hashing import verify_password
from app.auth.jwt_handler import create_access_token
from app.db.repositories.user_repo import UserRepository

router = APIRouter()


@router.post("/login")
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
):
    user = UserRepository(db).find_by_username(form.username)
    # Same error whether username is wrong or password is wrong — don't leak existence.
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(user.username, user.role)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
def me(current_user: CurrentUser):
    return {"username": current_user.username, "role": current_user.role}
