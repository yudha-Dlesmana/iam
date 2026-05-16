from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", 
        extra="ignore"
    )
    ENV: str = "development"
    PORT: int = 8000
    HOST: str = "localhost"

    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    MYSQL_ROOT_PASSWORD: str

    DB_URL: str
    TEST_DB_URL: str


settings = Settings()