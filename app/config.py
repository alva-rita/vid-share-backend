# config.py

# Use FastAPI's settings or direct os.getenv for environment variables
# For a university project, os.getenv is straightforward.
# For production, consider using Pydantic's BaseSettings for better validation.
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    secret_key: str
    database_url: str
    azure_storage_connection_string: str
    azure_blob_container_name: str
    azure_storage_account_name: str
    azure_storage_account_key: str
    pghost: str
    pguser: str
    pgport: str
    pgdatabase: str
    pgpassword: str 

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


SECRET_KEY = settings.secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

DATABASE_URL =settings.database_url
AZURE_STORAGE_CONNECTION_STRING = settings.azure_storage_connection_string
AZURE_BLOB_CONTAINER_NAME = settings.azure_blob_container_name
AZURE_STORAGE_ACCOUNT_NAME = settings.azure_storage_account_name
AZURE_STORAGE_ACCOUNT_KEY = settings.azure_storage_account_key