from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError, jwk
from jose.utils import base64url_decode
from app.config import get_settings
import httpx
import json

security = HTTPBearer()

_jwks_cache = None


async def get_jwks(supabase_url: str):
    global _jwks_cache
    if _jwks_cache is None:
        jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url)
            _jwks_cache = response.json()
    return _jwks_cache


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    token = credentials.credentials
    settings = get_settings()
    
    try:
        # First try with JWKS (ECC keys)
        jwks = await get_jwks(settings.supabase_url)
        
        # Get the key id from token header
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        rsa_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                rsa_key = key
                break
        
        if rsa_key:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=["ES256"],
                audience="authenticated",
            )
        else:
            # Fallback to legacy HS256
            payload = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
        
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        return {"id": user_id, "email": payload.get("email")}
    except JWTError as e:
        print(f"JWT Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
