import secrets
from fastapi import Request, HTTPException

def verify_csrf(request: Request):
    cookie_token = request.cookies.get("csrf_token")
    header_token = request.headers.get("X-CSRF-Token")

    if not cookie_token or not header_token:
        raise HTTPException(
            status_code = 403, 
            detail="CSRF token missing"
        )
    if not secrets.compare_digest(cookie_token, header_token):
        raise HTTPException(
            status_code = 403,
            detail="CSRF token mismatch"
        )