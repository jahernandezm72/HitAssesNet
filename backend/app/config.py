from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "dev"  # dev | prod
    database_url: str = "postgresql+psycopg://hitassesnet:devpass@localhost:5432/hitassesnet"
    jwt_secret: str = "change-me"
    jwt_hours: int = 12
    admin_email: str = "admin@hermoit.cloud"
    admin_password: str = "ChangeMe123!"
    admin_name: str = "Administrador"
    static_dir: str = ""  # si se define, la API también sirve landing (/) y app (/app) sin nginx
    cors_origins: str = ""  # lista separada por comas; vacío = sin CORS (mismo origen)


settings = Settings()

if settings.env == "prod" and (settings.jwt_secret == "change-me" or settings.admin_password == "ChangeMe123!"):
    raise RuntimeError("ENV=prod exige cambiar JWT_SECRET y ADMIN_PASSWORD")
