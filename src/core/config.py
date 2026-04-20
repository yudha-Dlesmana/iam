from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    DB_URL: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES:int = 30
    REFRESH_TOKEN_EXPIRES_DAYS:int = 7
    

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()