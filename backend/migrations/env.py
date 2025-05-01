import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from alembic import context

# Load .env
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

# Include parent dir for model imports
sys.path.append(str(Path(__file__).resolve().parents[1]))

from auth import Base  # Add more model imports if needed

config = context.config
db_url = os.getenv("DATABASE_URL")

if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

target_metadata = Base.metadata

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = create_engine(config.get_main_option("sqlalchemy.url"))
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
