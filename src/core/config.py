from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    ENV: str = "development"
    PORT: int = 8000
    HOST: str = "localhost"

    FRONTEND_URLs: str = "http://localhost:9000"
    COOKIE_DOMAIN: str = ""
    FORWARDED_ALLOW_IPS: str = ""

    DB_URL: str
    TEST_DB_URL: str

    REDIS_URL: str

    JWT_KEYS_DIR: str = "keys"
    JWT_ACTIVE_KID: str = "iam-key-1"
    JWT_ISSUER: str = "iam"
    JWT_REFRESH_SECRET: str

    @property
    def cors_origins(self) -> list[str]:
        return [u.strip() for u in self.FRONTEND_URLs.split(",") if u.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENV != "development"


settings = Settings()
