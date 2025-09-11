"""
Global error handling and retry mechanisms for demo stability
"""

import time
import logging
from typing import Any, Callable, Optional, TypeVar, Union
from functools import wraps
import asyncio
from fastapi import HTTPException
from fastapi.responses import JSONResponse

T = TypeVar('T')

class DemoErrorHandler:
    """Error handler with graceful degradation for demo environment"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.max_retries = 3
        self.timeout = 30  # seconds
        self.backoff_base = 2  # exponential backoff
        
    def with_retry(
        self, 
        max_retries: Optional[int] = None,
        timeout: Optional[int] = None,
        fallback: Optional[Callable] = None
    ):
        """Decorator for automatic retry with exponential backoff"""
        max_retries = max_retries or self.max_retries
        timeout = timeout or self.timeout
        
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(max_retries):
                    try:
                        # Add timeout
                        return await asyncio.wait_for(
                            func(*args, **kwargs),
                            timeout=timeout
                        )
                    except asyncio.TimeoutError:
                        self.logger.warning(
                            f"[TIMEOUT] {func.__name__} timed out after {timeout}s (attempt {attempt + 1}/{max_retries})"
                        )
                        last_exception = TimeoutError(f"Operation timed out after {timeout} seconds")
                    except Exception as e:
                        self.logger.warning(
                            f"[ERROR] {func.__name__} failed: {str(e)} (attempt {attempt + 1}/{max_retries})"
                        )
                        last_exception = e
                    
                    # Exponential backoff
                    if attempt < max_retries - 1:
                        wait_time = self.backoff_base ** attempt
                        await asyncio.sleep(wait_time)
                
                # All retries failed, use fallback if provided
                if fallback:
                    self.logger.info(f"[FALLBACK] Using fallback for {func.__name__}")
                    return await fallback(*args, **kwargs) if asyncio.iscoroutinefunction(fallback) else fallback(*args, **kwargs)
                
                # No fallback, raise the last exception
                raise last_exception
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(max_retries):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        self.logger.warning(
                            f"[ERROR] {func.__name__} failed: {str(e)} (attempt {attempt + 1}/{max_retries})"
                        )
                        last_exception = e
                    
                    # Exponential backoff
                    if attempt < max_retries - 1:
                        wait_time = self.backoff_base ** attempt
                        time.sleep(wait_time)
                
                # All retries failed, use fallback if provided
                if fallback:
                    self.logger.info(f"[FALLBACK] Using fallback for {func.__name__}")
                    return fallback(*args, **kwargs)
                
                # No fallback, raise the last exception
                raise last_exception
            
            # Return appropriate wrapper based on function type
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    def safe_api_call(self, default_response: Any = None):
        """Decorator for safe API calls with default response"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except HTTPException:
                    # Re-raise HTTP exceptions (they're intentional)
                    raise
                except Exception as e:
                    self.logger.error(f"[API ERROR] {func.__name__}: {str(e)}")
                    
                    # Return a friendly error response
                    if default_response is not None:
                        return default_response
                    
                    return {
                        "success": False,
                        "message": "Service temporarily unavailable. Please try again.",
                        "error_type": "service_error"
                    }
            
            return wrapper
        return decorator


# Global instance
error_handler = DemoErrorHandler()


# Utility functions for common error scenarios
async def with_timeout(coro, timeout: int = 30):
    """Execute coroutine with timeout"""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        raise TimeoutError(f"Operation timed out after {timeout} seconds")


def create_fallback_response(query: str, error: Optional[str] = None) -> dict:
    """Create a fallback response when services fail"""
    base_response = {
        "text": "I'm here to help with ALS-related questions. Due to a temporary issue, I'm providing a general response. Please try again or contact your healthcare provider for specific medical advice.",
        "confidence": 0.3,
        "source": "fallback",
        "has_error": True
    }
    
    if error:
        base_response["error_detail"] = error
    
    # Add context-specific fallback based on query keywords
    query_lower = query.lower()
    
    if any(word in query_lower for word in ["symptom", "weakness", "breathing", "swallow"]):
        base_response["text"] = "ALS symptoms can vary but often include muscle weakness, difficulty breathing, and swallowing challenges. Please consult your healthcare team for personalized assessment and management strategies."
    elif any(word in query_lower for word in ["treatment", "medication", "therapy"]):
        base_response["text"] = "ALS treatment typically includes medications like riluzole or edaravone, along with supportive therapies. Your healthcare team can provide the most appropriate treatment plan for your specific situation."
    elif any(word in query_lower for word in ["help", "support", "care"]):
        base_response["text"] = "Support for ALS includes medical care, physical therapy, assistive devices, and emotional support. Local ALS organizations can provide resources and connect you with support services."
    
    return base_response


# Middleware for global error catching
async def error_handling_middleware(request, call_next):
    """Global error handling middleware"""
    try:
        response = await call_next(request)
        return response
    except HTTPException:
        # Let HTTP exceptions pass through
        raise
    except Exception as e:
        logging.error(f"[UNHANDLED ERROR] {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "An unexpected error occurred. Please try again.",
                "error_type": "internal_error"
            }
        )