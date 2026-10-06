from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import get_current_user, require_admin
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.security import create_access_token, hash_password, verify_password


router = APIRouter(prefix="/auth", tags=["authentication"])


def issue_token(user: User) -> TokenResponse:
    return TokenResponse(access_token=create_access_token(str(user.id), user.role), user=user)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists.")
    user = User(email=payload.email.lower(), password_hash=hash_password(payload.password), role="user")
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists.") from error
    return issue_token(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password.", headers={"WWW-Authenticate": "Bearer"})
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive.")
    return issue_token(user)


@router.get("/me", response_model=UserResponse)
def current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.get("/admin-check")
def admin_check(_: User = Depends(require_admin)) -> dict[str, str]:
    return {"status": "ok", "message": "Admin access granted."}
