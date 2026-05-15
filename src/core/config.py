from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", 
        extra="ignore"
    )
    PORT: int = 8000
    HOST: str = "127.0.0.1"


settings = Settings()