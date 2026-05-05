from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ENV: str = "development" # "production" in prod
    FRONTEND_URL: str

    PORT: int = 8000
    HOST: str = "0.0.0.0"

    DB_URL: str
    REDIS_URL: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES:int = 30
    REFRESH_TOKEN_EXPIRE_DAYS:int = 7

    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str
    

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"

settings = Settings()