import json
import socket
from datetime import datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from config import (
    DETAIL_FIELDS,
    OMDB_API_KEY,
    TMDB_API_KEY,
    TMDB_IMAGE_BASE_URL,
    WATCHED_RETENTION_DAYS,
    YOUTUBE_API_KEY,
)
from database import update_tmdb_poster_path


def fetch_json(url, params=None, timeout=10):
    request_url = url
    if params:
        request_url = f"{url}?{urlencode(params)}"

    try:
        request = Request(
            request_url,
            headers={
                "User-Agent": "Mozilla/5.0 CineScope/2.0",
                "Accept": "application/json,text/plain,*/*",
            },
        )
        with urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8")
    except HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}") from exc
    except (URLError, socket.timeout) as exc:
        raise RuntimeError(f"Network error: {exc}") from exc


def fetch_bytes(url, timeout=10):
    try:
        request = Request(url, headers={"User-Agent": "Mozilla/5.0 CineScope/2.0"})
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    except HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}") from exc
    except (URLError, socket.timeout) as exc:
        raise RuntimeError(f"Network error: {exc}") from exc


def parse_date(date_string):
    if not date_string:
        return None
    try:
        return datetime.strptime(date_string, "%Y-%m-%d").date()
    except ValueError:
        return None


def format_date_label(date_string):
    watched_on = parse_date(date_string)
    if not watched_on:
        return ""
    return watched_on.strftime("%b %d, %Y")


def fetch_movie_data(movie_title, api_key=OMDB_API_KEY):
    params = {"t": movie_title, "apikey": api_key}
    last_error = None

    for url in ("https://www.omdbapi.com/", "http://www.omdbapi.com/"):
        try:
            payload = fetch_json(url, params=params, timeout=10)
            data = json.loads(payload)
            break
        except RuntimeError as exc:
            last_error = str(exc)
        except Exception:
            return {"error": "Received an invalid response from OMDb."}
    else:
        return {"error": last_error or "Movie lookup failed before OMDb returned data."}

    if data.get("Response") == "False":
        return {"error": data.get("Error", "Movie not found.")}
    return data


def search_tmdb_poster_path(movie_title, release_year=None):
    if not TMDB_API_KEY:
        return None

    params = {
        "api_key": TMDB_API_KEY,
        "query": movie_title,
        "include_adult": "false",
    }
    if release_year and str(release_year).isdigit():
        params["year"] = str(release_year)[:4]

    try:
        payload = fetch_json("https://api.themoviedb.org/3/search/movie", params=params)
        results = json.loads(payload).get("results", [])
    except Exception:
        return None

    for result in results:
        poster_path = result.get("poster_path")
        if poster_path:
            return poster_path
    return None


def get_tmdb_poster_url(movie_record, movie_data):
    poster_path = movie_record.get("tmdb_poster_path")
    if poster_path:
        return f"{TMDB_IMAGE_BASE_URL}{poster_path}"

    poster_path = search_tmdb_poster_path(
        movie_data.get("Title", movie_record["title"]),
        movie_data.get("Year", ""),
    )
    if poster_path:
        update_tmdb_poster_path(movie_record["id"], poster_path)
        return f"{TMDB_IMAGE_BASE_URL}{poster_path}"
    return None


def search_youtube_trailer(movie_title):
    if not YOUTUBE_API_KEY:
        return None

    params = {
        "part": "snippet",
        "q": f"{movie_title} trailer",
        "maxResults": 1,
        "type": "video",
        "key": YOUTUBE_API_KEY,
    }
    try:
        payload = fetch_json("https://www.googleapis.com/youtube/v3/search", params=params)
        results = json.loads(payload).get("items", [])
    except Exception:
        return None

    if not results:
        return None
    return f"https://www.youtube.com/watch?v={results[0]['id']['videoId']}"


def format_movie_data(movie_data, movie_record=None):
    lines = []
    for field in DETAIL_FIELDS:
        value = movie_data.get(field)
        if not value or value == "N/A":
            continue
        label = "IMDb Rating" if field == "imdbRating" else field
        lines.append(f"{label}: {value}")

    ratings = movie_data.get("Ratings", [])
    if ratings:
        joined_ratings = ", ".join(
            f"{rating['Source']}: {rating['Value']}" for rating in ratings
        )
        lines.append(f"Ratings: {joined_ratings}")

    if movie_record and movie_record.get("watched_at"):
        watched_on = parse_date(movie_record["watched_at"])
        if watched_on:
            rewatch_date = watched_on + timedelta(days=WATCHED_RETENTION_DAYS)
            lines.append(f"Watched On: {watched_on.isoformat()}")
            lines.append(f"Ready Again: {rewatch_date.isoformat()}")

    return "\n\n".join(lines)
