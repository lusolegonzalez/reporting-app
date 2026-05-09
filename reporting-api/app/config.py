import os

from dotenv import load_dotenv

load_dotenv()


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-dev-secret")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/reporting_api",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ADMIN_ROLE_NAME = os.getenv("ADMIN_ROLE_NAME", "ADMIN")
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
        if origin.strip()
    ]

    # ----- SQL Server origen (modo solo lectura) -----
    # Conexion desacoplada por variables de entorno. Si MSSQL_SERVER esta vacio
    # se considera "no configurado" y la fuente real no se puede instanciar.
    MSSQL_DRIVER = os.getenv("MSSQL_DRIVER", "{ODBC Driver 18 for SQL Server}")
    MSSQL_SERVER = os.getenv("MSSQL_SERVER", "")
    MSSQL_PORT = int(os.getenv("MSSQL_PORT", "1433"))
    MSSQL_DATABASE = os.getenv("MSSQL_DATABASE", "TwinsDbQuatro045")
    MSSQL_UID = os.getenv("MSSQL_UID", "")
    MSSQL_PWD = os.getenv("MSSQL_PWD", "")
    MSSQL_ENCRYPT = os.getenv("MSSQL_ENCRYPT", "no")
    MSSQL_TRUST_SERVER_CERTIFICATE = os.getenv("MSSQL_TRUST_SERVER_CERTIFICATE", "yes")
    # Timeouts en segundos
    MSSQL_LOGIN_TIMEOUT = int(os.getenv("MSSQL_LOGIN_TIMEOUT", "10"))
    MSSQL_QUERY_TIMEOUT = int(os.getenv("MSSQL_QUERY_TIMEOUT", "60"))


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True


class ProductionConfig(BaseConfig):
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
