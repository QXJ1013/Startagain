# app/routers/auth.py
"""
Authentication endpoints for user registration and login.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr, Field

from app.deps import get_storage, get_current_user as get_auth_user
from app.services.auth import auth_service

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# Request/Response models
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
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


class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = None
    email: Optional[EmailStr] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, description="New password must be at least 8 characters")


# Use the centralized auth dependency
# get_current_user is imported from deps.py


@router.post("/register", response_model=AuthResponse)
async def register(
    request: RegisterRequest,
    storage = Depends(get_storage)
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
    storage = Depends(get_storage)
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
async def get_me(current_user: dict = Depends(get_auth_user)):
    """Get current user information"""
    return UserResponse(
        user_id=current_user["id"],
        email=current_user["email"],
        display_name=current_user["display_name"]
    )


@router.post("/verify")
async def verify_token(current_user: dict = Depends(get_auth_user)):
    """Verify if token is valid"""
    return {"valid": True, "user_id": current_user["id"]}


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: dict = Depends(get_auth_user),
    storage = Depends(get_storage)
):
    """Update user profile information"""
    try:
        result = auth_service.update_user_profile(
            storage=storage,
            user_id=current_user["id"],
            display_name=request.display_name,
            email=request.email
        )
        return UserResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        print(f"Profile update error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Profile update failed: {str(e)}")


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_auth_user),
    storage = Depends(get_storage)
):
    """Change user password"""
    try:
        auth_service.change_user_password(
            storage=storage,
            user_id=current_user["id"],
            current_password=request.current_password,
            new_password=request.new_password
        )
        return {"message": "Password changed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        print(f"Password change error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Password change failed: {str(e)}")