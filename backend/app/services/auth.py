# app/services/auth.py
"""
Authentication service for user management and JWT handling.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import uuid

from passlib.context import CryptContext
import jwt
from email_validator import validate_email, EmailNotValidError

from app.config import get_settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Settings
settings = get_settings()

# JWT Configuration
SECRET_KEY = getattr(settings, "SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours for simplicity


class AuthService:
    """Handle authentication operations"""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)
    
    @staticmethod
    def validate_email_address(email: str) -> str:
        """Validate and normalize email address"""
        try:
            validation = validate_email(email, check_deliverability=False)
            return validation.email.lower()
        except EmailNotValidError as e:
            raise ValueError(f"Invalid email: {str(e)}")
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
        """Decode and validate JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            return None  # Token expired
        except Exception:
            return None  # Invalid token
    
    def register_user(self, storage, email: str, password: str, display_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Register a new user
        Returns user data and access token
        """
        # Validate email
        email = self.validate_email_address(email)
        
        # Check if user exists
        existing = storage.get_user_by_email(email)
        if existing:
            raise ValueError("Email already registered")
        
        # Create user
        user_id = str(uuid.uuid4())
        hashed_password = self.hash_password(password)
        
        storage.create_user(
            user_id=user_id,
            email=email,
            password_hash=hashed_password,
            display_name=display_name or email.split('@')[0]
        )
        
        # Create access token
        access_token = self.create_access_token({"sub": user_id, "email": email})
        
        return {
            "user_id": user_id,
            "email": email,
            "display_name": display_name or email.split('@')[0],
            "access_token": access_token,
            "token_type": "bearer"
        }
    
    def login_user(self, storage, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user and return token
        """
        # Validate email format
        email = self.validate_email_address(email)
        
        # Get user
        user = storage.get_user_by_email(email)
        if not user:
            raise ValueError("Invalid email or password")
        
        # Verify password
        if not self.verify_password(password, user['password_hash']):
            raise ValueError("Invalid email or password")
        
        # Check if user is active
        if not user.get('is_active', True):
            raise ValueError("Account is disabled")
        
        # Update last login
        storage.update_user_last_login(user['id'])
        
        # Create access token
        access_token = self.create_access_token({"sub": user['id'], "email": user['email']})
        
        return {
            "user_id": user['id'],
            "email": user['email'],
            "display_name": user['display_name'],
            "access_token": access_token,
            "token_type": "bearer"
        }
    
    def get_current_user(self, storage, token: str) -> Optional[Dict[str, Any]]:
        """
        Get user from JWT token
        """
        payload = self.decode_access_token(token)
        if not payload:
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        user = storage.get_user_by_id(user_id)
        if not user or not user.get('is_active', True):
            return None
        
        return user


# Global instance
auth_service = AuthService()