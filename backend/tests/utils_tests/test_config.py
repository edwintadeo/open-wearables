from pydantic import SecretStr

from app.config import Settings


def test_db_uri_uses_host_and_port_by_default() -> None:
    settings = Settings(
        secret_key="test-secret",
        db_host="db",
        db_port=5432,
        db_name="open_wearables",
        db_user="open_wearables_app",
        db_password=SecretStr("p@ss/word"),
    )

    assert settings.db_uri == (
        "postgresql+psycopg://open_wearables_app:p%40ss%2Fword@db:5432/open_wearables"
    )
    assert settings.db_uri_for_configparser == (
        "postgresql+psycopg://open_wearables_app:p%%40ss%%2Fword@db:5432/open_wearables"
    )
    assert settings.db_connection_kwargs == {
        "host": "db",
        "port": 5432,
        "dbname": "open_wearables",
        "user": "open_wearables_app",
        "password": "p@ss/word",
    }


def test_db_uri_uses_cloud_sql_socket_when_instance_connection_name_is_set() -> None:
    settings = Settings(
        secret_key="test-secret",
        db_name="open_wearables",
        db_user="open_wearables_app",
        db_password=SecretStr("p@ss/word"),
        db_instance_connection_name="app-seguimiento-nutricion:europe-west1:medical-companion-db",
    )

    assert settings.db_uri == (
        "postgresql+psycopg://open_wearables_app:p%40ss%2Fword@/open_wearables"
        "?host=%2Fcloudsql%2Fapp-seguimiento-nutricion%3Aeurope-west1%3Amedical-companion-db"
    )
    assert settings.db_uri_for_configparser == (
        "postgresql+psycopg://open_wearables_app:p%%40ss%%2Fword@/open_wearables"
        "?host=%%2Fcloudsql%%2Fapp-seguimiento-nutricion%%3Aeurope-west1%%3Amedical-companion-db"
    )
    assert settings.db_connection_kwargs == {
        "host": "/cloudsql/app-seguimiento-nutricion:europe-west1:medical-companion-db",
        "dbname": "open_wearables",
        "user": "open_wearables_app",
        "password": "p@ss/word",
    }
