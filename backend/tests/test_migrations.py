from alembic import command
from sqlalchemy import create_engine, inspect


def table_names(url: str) -> list[str]:
    engine = create_engine(url)
    try:
        return inspect(engine).get_table_names()
    finally:
        engine.dispose()  # releases the file so Windows can clean up the temp folder


def test_migrations_build_the_schema_match_the_models_and_roll_back(tmp_path, alembic_config_factory):
    url = f"sqlite:///{(tmp_path / 'fresh.db').as_posix()}"
    config = alembic_config_factory(url)

    command.upgrade(config, "head")
    command.check(config)  # raises if the models and the migrations disagree
    assert "users" in table_names(url)

    command.downgrade(config, "base")
    assert "users" not in table_names(url)