import os
from functools import lru_cache
from pathlib import Path

import dotenv

<<<<<<< HEAD
APP_VERSION = "v0.5.6"
DB_VERSION = "v0.5.0"
=======
from mealie.core.settings import app_settings_constructor

from .settings import AppDirectories, AppSettings
from .settings.static import APP_VERSION, DB_VERSION

APP_VERSION
DB_VERSION
>>>>>>> v1.0.0-beta-1

CWD = Path(__file__).parent
BASE_DIR = CWD.parent.parent
ENV = BASE_DIR.joinpath(".env")

dotenv.load_dotenv(ENV)
PRODUCTION = os.getenv("PRODUCTION", "True").lower() in ["true", "1"]
TESTING = os.getenv("TESTING", "False").lower() in ["true", "1"]


def determine_data_dir() -> Path:
    global PRODUCTION, TESTING, BASE_DIR

    if TESTING:
        return BASE_DIR.joinpath("tests/.temp")

<<<<<<< HEAD
def determine_sqlite_path(path=False, suffix=DB_VERSION) -> str:
    global app_dirs
    db_path = app_dirs.DATA_DIR.joinpath(f"mealie_{suffix}.db")  # ! Temporary Until Alembic

    if path:
        return db_path

    return "sqlite:///" + str(db_path.absolute())


class AppSettings(BaseSettings):
    global DATA_DIR
    PRODUCTION: bool = Field(True, env="PRODUCTION")
    BASE_URL: str = "http://localhost:8080"
    IS_DEMO: bool = False
    API_PORT: int = 9000
    API_DOCS: bool = True

    @property
    def DOCS_URL(self) -> str:
        return "/docs" if self.API_DOCS else None

    @property
    def REDOC_URL(self) -> str:
        return "/redoc" if self.API_DOCS else None

    SECRET: str = determine_secrets(DATA_DIR, PRODUCTION)

    DB_ENGINE: str = "sqlite"  # Optional: 'sqlite', 'postgres'
    POSTGRES_USER: str = "mealie"
    POSTGRES_PASSWORD: str = "mealie"
    POSTGRES_SERVER: str = "postgres"
    POSTGRES_PORT: str = 5432
    POSTGRES_DB: str = "mealie"

    DB_URL: Union[str, PostgresDsn] = None  # Actual DB_URL is calculated with `assemble_db_connection`

    @validator("DB_URL", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: dict[str, Any]) -> Any:
        engine = values.get("DB_ENGINE", "sqlite")
        if engine == "postgres":
            host = f"{values.get('POSTGRES_SERVER')}:{values.get('POSTGRES_PORT')}"
            return PostgresDsn.build(
                scheme="postgresql",
                user=values.get("POSTGRES_USER"),
                password=values.get("POSTGRES_PASSWORD"),
                host=host,
                path=f"/{values.get('POSTGRES_DB') or ''}",
            )
        return determine_sqlite_path()

    DB_URL_PUBLIC: str = ""  # hide credentials to show on logs/frontend

    @validator("DB_URL_PUBLIC", pre=True)
    def public_db_url(cls, v: Optional[str], values: dict[str, Any]) -> str:
        url = values.get("DB_URL")
        engine = values.get("DB_ENGINE", "sqlite")
        if engine != "postgres":
            # sqlite
            return url

        user = values.get("POSTGRES_USER")
        password = values.get("POSTGRES_PASSWORD")
        return url.replace(user, "*****", 1).replace(password, "*****", 1)

    DEFAULT_GROUP: str = "Home"
    DEFAULT_EMAIL: str = "changeme@email.com"
    DEFAULT_PASSWORD: str = "MyPassword"

    LDAP_AUTH_ENABLED: bool = False
    LDAP_SERVER_URL: str = None
    LDAP_BIND_TEMPLATE: str = None
    LDAP_ADMIN_FILTER: str = None

    SCHEDULER_DATABASE = f"sqlite:///{app_dirs.DATA_DIR.joinpath('scheduler.db')}"

    TOKEN_TIME: int = 2  # Time in Hours
=======
    if PRODUCTION:
        return Path("/app/data")
>>>>>>> v1.0.0-beta-1

    return BASE_DIR.joinpath("dev", "data")


<<<<<<< HEAD
    AUTO_BACKUP_ENABLED: bool = False

    class Config:
        env_file = BASE_DIR.joinpath(".env")
        env_file_encoding = "utf-8"
=======
@lru_cache
def get_app_dirs() -> AppDirectories:
    return AppDirectories(determine_data_dir())
>>>>>>> v1.0.0-beta-1


@lru_cache
def get_app_settings() -> AppSettings:
    return app_settings_constructor(env_file=ENV, production=PRODUCTION, data_dir=determine_data_dir())
