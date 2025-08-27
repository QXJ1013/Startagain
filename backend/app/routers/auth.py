# app/routers/auth.py
"""
Authentication endpoints for user registration and login.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr, Field

from app.services.storage import Storage
from app.services.auth import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


# Request/Response models
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")
    display_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    user_id: str
    email: str
    display_name: str
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    user_id: str
    email: str
    display_name: str


# Dependency to get storage
def get_storage() -> Storage:
    return Storage()


# Dependency to get current user from token
async def get_current_user(
    authorization: Optional[str] = Header(None),
    storage: Storage = Depends(get_storage)
) -> dict:
    """Extract and validate user from Authorization header"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Extract token from "Bearer <token>"
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    # Validate token and get user
    user = auth_service.get_current_user(storage, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return user


@router.post("/register", response_model=AuthResponse)
async def register(
    request: RegisterRequest,
    storage: Storage = Depends(get_storage)
):
    """Register a new user"""
    try:
        result = auth_service.register_user(
            storage=storage,
            email=request.email,
            password=request.password,
            display_name=request.display_name
        )
        return AuthResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        print(f"Registration error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    storage: Storage = Depends(get_storage)
):
    """Login with email and password"""
    try:
        result = auth_service.login_user(
            storage=storage,
            email=request.email,
            password=request.password
        )
        return AuthResponse(**result)
    except ValueError as e:
        # Don't reveal whether email exists or password is wrong
        raise HTTPException(status_code=401, detail="Invalid email or password")
    except Exception as e:
        import traceback
        print(f"Login error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(
        user_id=current_user["id"],
        email=current_user["email"],
        display_name=current_user["display_name"]
    )


@router.post("/verify")
async def verify_token(current_user: dict = Depends(get_current_user)):
    """Verify if token is valid"""
    return {"valid": True, "user_id": current_user["id"]}