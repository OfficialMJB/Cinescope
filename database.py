import sqlite3
from datetime import date, timedelta
from tkinter import messagebox

from config import DATABASE_PATH, WATCHED_RETENTION_DAYS


def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_column(conn, column_name, column_definition):
    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(movies)").fetchall()
    }
    if column_name not in columns:
        conn.execute(f"ALTER TABLE movies ADD COLUMN {column_name} {column_definition}")


def initialize_db():
    try:
        with get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS movies (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL
                )
                """
            )
            ensure_column(conn, "watched_at", "TEXT")
            ensure_column(conn, "tmdb_poster_path", "TEXT")
            conn.commit()
    except sqlite3.Error as exc:
        messagebox.showerror(
            "Database Error",
            f"Error occurred while initializing the database:\n{exc}",
        )


def expire_seen_movies():
    cutoff = (date.today() - timedelta(days=WATCHED_RETENTION_DAYS)).isoformat()
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE movies
                SET watched_at = NULL
                WHERE watched_at IS NOT NULL
                  AND watched_at <= ?
                """,
                (cutoff,),
            )
            conn.commit()
        return cursor.rowcount
    except sqlite3.Error as exc:
        messagebox.showerror(
            "Database Error",
            f"Error occurred while expiring watched movies:\n{exc}",
        )
        return 0


def load_movies():
    try:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, title, watched_at, tmdb_poster_path
                FROM movies
                ORDER BY LOWER(title), id
                """
            ).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as exc:
        messagebox.showerror(
            "Database Error",
            f"Error occurred while loading movies:\n{exc}",
        )
        return []


def movie_exists(title, exclude_id=None):
    normalized_title = title.strip().lower()
    query = "SELECT 1 FROM movies WHERE LOWER(TRIM(title)) = ?"
    params = [normalized_title]
    if exclude_id is not None:
        query += " AND id != ?"
        params.append(exclude_id)
    query += " LIMIT 1"

    try:
        with get_connection() as conn:
            row = conn.execute(query, tuple(params)).fetchone()
        return row is not None
    except sqlite3.Error as exc:
        messagebox.showerror(
            "Database Error",
            f"Error occurred while checking for duplicates:\n{exc}",
        )
        return False


def add_movie_db(title):
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO movies (title, watched_at, tmdb_poster_path) VALUES (?, NULL, NULL)",
                (title.strip(),),
            )
            conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as exc:
        messagebox.showerror(
            "Database Error",
            f"Error occurred while adding the movie:\n{exc}",
        )
        return None


def update_movie_db(movie_id, new_title):
    try:
        with get_connection() as conn:
            conn.execute(
                "UPDATE movies SET title = ?, tmdb_poster_path = NULL WHERE id = ?",
                (new_title.strip(), movie_id),
            )
            conn.commit()
    except sqlite3.Error as exc:
        messagebox.showerror(
            "Database Error",
            f"Error occurred while updating the movie:\n{exc}",
        )


def delete_movie_db(movie_id):
    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
            conn.commit()
    except sqlite3.Error as exc:
        messagebox.showerror(
            "Database Error",
            f"Error occurred while deleting the movie:\n{exc}",
        )


def mark_movie_seen_db(movie_id, watched_at):
    try:
        with get_connection() as conn:
            conn.execute(
                "UPDATE movies SET watched_at = ? WHERE id = ?",
                (watched_at, movie_id),
            )
            conn.commit()
    except sqlite3.Error as exc:
        messagebox.showerror(
            "Database Error",
            f"Error occurred while marking the movie as seen:\n{exc}",
        )


def reset_movie_to_watchlist_db(movie_id):
    try:
        with get_connection() as conn:
            conn.execute(
                "UPDATE movies SET watched_at = NULL WHERE id = ?",
                (movie_id,),
            )
            conn.commit()
    except sqlite3.Error as exc:
        messagebox.showerror(
            "Database Error",
            f"Error occurred while moving the movie back to the watchlist:\n{exc}",
        )


def update_tmdb_poster_path(movie_id, poster_path):
    try:
        with get_connection() as conn:
            conn.execute(
                "UPDATE movies SET tmdb_poster_path = ? WHERE id = ?",
                (poster_path, movie_id),
            )
            conn.commit()
    except sqlite3.Error:
        pass
