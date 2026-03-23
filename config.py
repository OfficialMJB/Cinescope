import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "movies.db"
APP_TITLE = "CineScope"
WATCHED_RETENTION_DAYS = 180
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
ENV_FILE_PATH = BASE_DIR / ".env"
DETAIL_FIELDS = [
    "Title",
    "Year",
    "Rated",
    "Runtime",
    "Genre",
    "Director",
    "Writer",
    "Actors",
    "Plot",
    "Language",
    "Country",
    "Awards",
    "imdbRating",
    "BoxOffice",
    "Production",
]


def load_env_file(env_path):
    if not env_path.exists():
        return

    try:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            if key:
                os.environ.setdefault(key, value)
    except OSError:
        pass


load_env_file(ENV_FILE_PATH)

OMDB_API_KEY = os.getenv("OMDB_API_KEY", "")
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
