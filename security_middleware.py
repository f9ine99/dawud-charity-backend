"""
Security Middleware for Dawud Charity Hub
Includes rate limiting, security headers, and request validation
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import re

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to all responses
    """
    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)
        
        # Security Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
            "img-src 'self' data: blob:; "
            "font-src 'self' https://cdnjs.cloudflare.com; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        
        return response


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Validates and sanitizes incoming requests
    """
    
    # Suspicious patterns to detect
    SQL_INJECTION_PATTERNS = [
        r"(\bunion\b.*\bselect\b)",
        r"(\bor\b.*=.*)",
        r"(--|\#|\/\*)",
        r"(\bexec\b|\bexecute\b)",
        r"(\bdrop\b.*\btable\b)",
        r"(\binsert\b.*\binto\b)",
        r"(\bupdate\b.*\bset\b)",
        r"(\bdelete\b.*\bfrom\b)"
    ]
    
    XSS_PATTERNS = [
        r"(<script[^>]*>.*?</script>)",
        r"(javascript:)",
        r"(on\w+\s*=)",
        r"(<iframe[^>]*>)",
        r"(<object[^>]*>)",
        r"(<embed[^>]*>)"
    ]
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Skip validation for safe methods and certain paths
        if request.method in ["GET", "OPTIONS"] or request.url.path.startswith("/admin/assets"):
            return await call_next(request)
        
        # Validate request body for POST/PUT/DELETE
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            try:
                # Check content length
                content_length = request.headers.get("content-length")
                if content_length and int(content_length) > 5 * 1024 * 1024:  # 5MB limit
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "Request payload too large. Maximum size is 5MB."}
                    )
                
                # Get request body if it's JSON
                if request.headers.get("content-type") == "application/json":
                    try:
                        body = await request.body()
                        body_str = body.decode('utf-8')
                        
                        # Check for SQL injection patterns
                        for pattern in self.SQL_INJECTION_PATTERNS:
                            if re.search(pattern, body_str, re.IGNORECASE):
                                return JSONResponse(
                                    status_code=400,
                                    content={"detail": "Invalid input detected"}
                                )
                        
                        # Check for XSS patterns
                        for pattern in self.XSS_PATTERNS:
                            if re.search(pattern, body_str, re.IGNORECASE):
                                return JSONResponse(
                                    status_code=400,
                                    content={"detail": "Invalid input detected"}
                                )
                    except:
                        pass  # Not JSON or can't decode, continue
            
            except Exception as e:
                print(f"Request validation error: {e}")
        
        return await call_next(request)


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """
    Optional IP whitelist for admin endpoints
    Set ADMIN_IP_WHITELIST environment variable to enable
    """
    
    def __init__(self, app, whitelist: list = None):
        super().__init__(app)
        self.whitelist = whitelist or []
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Only check admin endpoints if whitelist is configured
        if self.whitelist and request.url.path.startswith("/api/admin"):
            client_ip = get_remote_address(request)
            
            if client_ip not in self.whitelist:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Access denied from this IP address"}
                )
        
        return await call_next(request)


def setup_rate_limits(app):
    """
    Configure rate limits for different endpoints
    """
    # Add rate limit exception handler
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    return limiter

