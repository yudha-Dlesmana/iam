from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    DB_URL: str

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()