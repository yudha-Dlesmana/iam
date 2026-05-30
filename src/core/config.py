from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    ENV: str = "development"
    PORT: int = 8000
    HOST: str = "localhost"

    FRONTEND_URLs: str = "http://localhost:9000"
    COOKIE_DOMAIN: str = ""

    DB_URL: str
    TEST_DB_URL: str

    REDIS_URL: str

    JWT_PRIVATE_KEY_PATH: str = "jwt_private.pem"
    JWT_PUBLIC_KEY_PATH: str = "jwt_public.pem"
    JWT_ISSUER: str = "iam"
    JWT_REFRESH_SECRET: str

    @property
    def cors_origins(self) -> list[str]:
        return [u.strip() for u in self.FRONTEND_URLs.split(",") if u.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENV != "development"

    @property
    def jwt_private_key(self) -> str:
        with open(self.JWT_PRIVATE_KEY_PATH) as f:
            return f.read()

    @property
    def jwt_public_key(self) -> str:
        with open(self.JWT_PUBLIC_KEY_PATH) as f:
            return f.read()


settings = Settings()
