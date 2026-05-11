from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "AssetOps"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8080
    APP_ENVIORNMENT: str = "dev"

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "assetops"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"

    class Config:
        env_file = ".env"

settings = Settings()