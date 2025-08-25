from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Mi App de Certificados"
    environment: str = "development"
    debug: bool = True
    GOOGLE_CREDENTIALS_JSON: str
    SHEET_ID: str
    DRIVE_FOLDER_ID: str
    PORT: int = 8000

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
