from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_business
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.models import Business
from app.schemas.schemas import BusinessOut, RegisterIn, Token

router = APIRouter()


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.query(Business).filter(Business.email == email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    business = Business(
        name=data.business_name,
        email=email,
        hashed_password=hash_password(data.password),
        timezone=data.timezone,
    )
    db.add(business)
    db.commit()
    return Token(access_token=create_access_token(business.id))


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    business = db.query(Business).filter(Business.email == form.username.lower()).first()
    if not business or not verify_password(form.password, business.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(business.id))


@router.get("/me", response_model=BusinessOut)
def me(business: Business = Depends(get_current_business)):
    return business
