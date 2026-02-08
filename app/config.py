from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_jwt_secret: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""

    class Config:
        env_file = ".env"


def get_settings() -> Settings:
    return Settings()
