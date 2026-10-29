import os

from dotenv import load_dotenv

# Reads a local .env file if there is one (running without Docker).
# In Docker, docker compose passes the same values in with env_file.
load_dotenv()

# No default on purpose: the app must refuse to start without a real secret.
SECRET_KEY = os.environ["SECRET_KEY"]

ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "30"))

# Postgres in Docker sets DATABASE_URL; without it we keep using SQLite.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///tasks.db")