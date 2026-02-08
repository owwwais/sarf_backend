import logging
import time
from fastapi import APIRouter, HTTPException, status
from app.database import get_supabase
from app.schemas.user import UserCreate, UserLogin, UserResponse, TokenResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    supabase = get_supabase()
    try:
        logger.info(f"Registration attempt for: {user_data.email}")
        response = supabase.auth.sign_up({
            "email": user_data.email,
            "password": user_data.password,
        })

        if response.user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="فشل إنشاء الحساب، تأكد من البريد الإلكتروني",
            )

        if response.session is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="تم إنشاء الحساب لكن يجب تأكيد البريد الإلكتروني أولاً. تحقق من بريدك.",
            )

        user_id = response.user.id
        logger.info(f"User created in auth: {user_id}")

        # Wait for DB trigger to create user profile
        user_profile = None
        for attempt in range(5):
            try:
                result = supabase.table("users").select("*").eq("id", user_id).single().execute()
                user_profile = result.data
                break
            except Exception:
                logger.info(f"Waiting for user profile (attempt {attempt + 1})...")
                time.sleep(0.5)

        if user_profile is None:
            # Create profile manually if trigger didn't fire
            logger.info("Creating user profile manually")
            supabase.table("users").insert({
                "id": str(user_id),
                "email": user_data.email,
                "currency_code": user_data.currency_code,
                "is_onboarded": False,
            }).execute()
            result = supabase.table("users").select("*").eq("id", user_id).single().execute()
            user_profile = result.data

        if user_data.currency_code != "SAR":
            supabase.table("users").update({"currency_code": user_data.currency_code}).eq("id", user_id).execute()
            result = supabase.table("users").select("*").eq("id", user_id).single().execute()
            user_profile = result.data

        return TokenResponse(
            access_token=response.session.access_token,
            user=UserResponse(**user_profile),
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e).lower()
        logger.error(f"Registration error: {e}")

        if "rate limit" in error_msg:
            detail = "تم تجاوز عدد المحاولات المسموح. حاول مرة أخرى لاحقاً."
        elif "already registered" in error_msg or "already been registered" in error_msg:
            detail = "هذا البريد الإلكتروني مسجل مسبقاً. جرّب تسجيل الدخول."
        elif "invalid" in error_msg and "email" in error_msg:
            detail = "البريد الإلكتروني غير صالح. تأكد من كتابته بشكل صحيح."
        elif "password" in error_msg:
            detail = "كلمة المرور ضعيفة. يجب أن تكون 6 أحرف على الأقل."
        else:
            detail = f"فشل التسجيل: {str(e)}"

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )


@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    supabase = get_supabase()
    try:
        response = supabase.auth.sign_in_with_password({
            "email": user_data.email,
            "password": user_data.password,
        })
        if response.user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )
        user_profile = supabase.table("users").select("*").eq("id", response.user.id).single().execute()
        return TokenResponse(
            access_token=response.session.access_token,
            user=UserResponse(**user_profile.data),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )


@router.post("/logout")
async def logout():
    supabase = get_supabase()
    try:
        supabase.auth.sign_out()
        return {"message": "Logged out successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
