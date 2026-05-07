from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", 
        extra="ignore"
    )

    ENV: str = "development" # "production" in prod
    FRONTEND_URL: str
    FRONTEND_URL_DEV: str

    PORT: int = 8000
    HOST: str = "0.0.0.0"

    DB_URL: str
    TEST_DB_URL: str | None = None
    REDIS_URL: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES:int = 30
    REFRESH_TOKEN_EXPIRE_DAYS:int = 7

    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"

settings = Settings()