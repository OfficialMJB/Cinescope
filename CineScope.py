import json
import os
import random
import socket
import sqlite3
import webbrowser
from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import tkinter as tk
from tkinter import Canvas, Scrollbar, Text, Toplevel, messagebox, simpledialog, ttk

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "movies.db"
APP_TITLE = "CineScope"
WATCHED_RETENTION_DAYS = 180
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
API_KEY = os.getenv("OMDB_API_KEY", "4d0bba69")
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
YOUTUBE_API_KEY = os.getenv(
    "YOUTUBE_API_KEY",
    "AIzaSyAhml0RXXKDIeF7wnu6TBXC_UdVJxQ-IPs",
)
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


def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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


def fetch_movie_data(movie_title, api_key):
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


def set_status(status_var, message):
    status_var.set(message)


def get_selected_movie(listbox):
    selection = listbox.curselection()
    if not selection:
        return None
    index = selection[0]
    records = getattr(listbox, "movie_records", [])
    if index >= len(records):
        return None
    return records[index]


def format_watchlist_item(movie_record):
    return movie_record["title"]


def format_seen_item(movie_record):
    watched_on = format_date_label(movie_record.get("watched_at"))
    if not watched_on:
        return movie_record["title"]
    return f"{movie_record['title']}  |  watched {watched_on}"


def refresh_lists(watchlist_box, seen_box, notebook, status_var, message=None):
    expired_count = expire_seen_movies()
    records = load_movies()
    watchlist = [movie for movie in records if not movie.get("watched_at")]
    seen = [movie for movie in records if movie.get("watched_at")]

    watchlist_box.delete(0, tk.END)
    seen_box.delete(0, tk.END)
    watchlist_box.movie_records = watchlist
    seen_box.movie_records = seen

    for record in watchlist:
        watchlist_box.insert(tk.END, format_watchlist_item(record))
    for record in seen:
        seen_box.insert(tk.END, format_seen_item(record))

    notebook.tab(0, text=f"Watchlist ({len(watchlist)})")
    notebook.tab(1, text=f"Have Seen ({len(seen)})")

    if message:
        set_status(status_var, message)
    elif expired_count:
        set_status(
            status_var,
            f"{expired_count} movie moved back into your watchlist for a rewatch.",
        )
    else:
        set_status(
            status_var,
            f"{len(watchlist)} watchlist titles and {len(seen)} recently seen.",
        )


def add_movie(movie_entry, watchlist_box, seen_box, notebook, status_var):
    movie = movie_entry.get().strip()
    if not movie:
        messagebox.showwarning("Input Error", "Please enter a movie name.")
        return

    if movie_exists(movie):
        messagebox.showinfo("Duplicate Movie", f'"{movie}" is already in your library.')
        return

    movie_id = add_movie_db(movie)
    if movie_id is None:
        return

    movie_entry.delete(0, tk.END)
    refresh_lists(
        watchlist_box,
        seen_box,
        notebook,
        status_var,
        message=f'Added "{movie}" to your watchlist.',
    )


def delete_movie(listbox, watchlist_box, seen_box, notebook, status_var):
    selected = get_selected_movie(listbox)
    if not selected:
        messagebox.showinfo("Select a Movie", "Choose a movie to delete first.")
        return

    confirmed = messagebox.askyesno(
        "Delete Movie",
        f'Remove "{selected["title"]}" from CineScope?',
    )
    if not confirmed:
        return

    delete_movie_db(selected["id"])
    refresh_lists(
        watchlist_box,
        seen_box,
        notebook,
        status_var,
        message=f'Deleted "{selected["title"]}".',
    )


def edit_movie(movie_entry, listbox, watchlist_box, seen_box, notebook, status_var):
    selected = get_selected_movie(listbox)
    if not selected:
        messagebox.showinfo("Select a Movie", "Choose a movie to rename first.")
        return

    new_title = movie_entry.get().strip()
    if not new_title:
        messagebox.showwarning("Input Error", "Please enter a new movie name.")
        return

    if movie_exists(new_title, exclude_id=selected["id"]):
        messagebox.showinfo(
            "Duplicate Movie",
            f'"{new_title}" is already in your library.',
        )
        return

    update_movie_db(selected["id"], new_title)
    movie_entry.delete(0, tk.END)
    refresh_lists(
        watchlist_box,
        seen_box,
        notebook,
        status_var,
        message=f'Renamed "{selected["title"]}" to "{new_title}".',
    )


def prompt_for_watched_date():
    suggested_date = date.today().isoformat()
    watched_input = simpledialog.askstring(
        "Date Watched",
        "When did you watch it? Use YYYY-MM-DD.",
        initialvalue=suggested_date,
    )
    if watched_input is None:
        return None

    watched_on = parse_date(watched_input.strip())
    if not watched_on:
        messagebox.showerror("Invalid Date", "Please use the format YYYY-MM-DD.")
        return None
    if watched_on > date.today():
        messagebox.showerror("Invalid Date", "The watched date cannot be in the future.")
        return None
    return watched_on.isoformat()


def mark_movie_seen(listbox, watchlist_box, seen_box, notebook, status_var):
    selected = get_selected_movie(listbox)
    if not selected:
        messagebox.showinfo("Select a Movie", "Choose a movie to mark as seen.")
        return

    watched_at = prompt_for_watched_date()
    if watched_at is None:
        return

    mark_movie_seen_db(selected["id"], watched_at)
    refresh_lists(
        watchlist_box,
        seen_box,
        notebook,
        status_var,
        message=f'"{selected["title"]}" moved to Have Seen.',
    )


def move_back_to_watchlist(listbox, watchlist_box, seen_box, notebook, status_var):
    selected = get_selected_movie(listbox)
    if not selected:
        messagebox.showinfo("Select a Movie", "Choose a movie to move back first.")
        return

    reset_movie_to_watchlist_db(selected["id"])
    refresh_lists(
        watchlist_box,
        seen_box,
        notebook,
        status_var,
        message=f'"{selected["title"]}" is back on your watchlist.',
    )


def pick_random_movie(watchlist_box, status_var):
    records = getattr(watchlist_box, "movie_records", [])
    if not records:
        messagebox.showinfo("No Watchlist Titles", "Add a few movies first.")
        return

    choice = random.choice(records)
    set_status(status_var, f'Tonight\'s pick: "{choice["title"]}"')
    messagebox.showinfo(
        "Movie Night Pick",
        f'Tonight\'s random pick is:\n\n{choice["title"]}',
    )


def populate_entry_from_selection(event, movie_entry, listbox, *other_listboxes):
    selected = get_selected_movie(listbox)
    if not selected:
        return

    for other in other_listboxes:
        other.selection_clear(0, tk.END)

    movie_entry.delete(0, tk.END)
    movie_entry.insert(0, selected["title"])


def display_poster(poster_frame, poster_url):
    if not poster_url:
        ttk.Label(
            poster_frame,
            text="No poster available",
            style="Muted.TLabel",
            justify="center",
        ).pack(fill="both", expand=True)
        return

    if Image is None or ImageTk is None:
        ttk.Label(
            poster_frame,
            text="Install Pillow in the same Python environment to show posters.",
            style="Muted.TLabel",
            justify="center",
            wraplength=240,
        ).pack(fill="both", expand=True)
        return

    try:
        image_bytes = fetch_bytes(poster_url, timeout=10)
        image = Image.open(BytesIO(image_bytes))
        image.thumbnail((320, 460))
        photo_img = ImageTk.PhotoImage(image)

        canvas = Canvas(
            poster_frame,
            width=320,
            height=460,
            bg="#161d24",
            highlightthickness=0,
        )
        canvas.pack(fill="both", expand=True)
        canvas.create_image(160, 230, image=photo_img, anchor="center")
        canvas.image = photo_img
    except Exception as exc:
        ttk.Label(
            poster_frame,
            text=f"Poster unavailable\n{exc}",
            style="Muted.TLabel",
            justify="center",
            wraplength=240,
        ).pack(fill="both", expand=True)


def on_movie_double_click(event, movie_listbox, status_var):
    selected = get_selected_movie(movie_listbox)
    if not selected:
        return

    movie_title = selected["title"]
    set_status(status_var, f'Loading details for "{movie_title}"...')
    movie_data = fetch_movie_data(movie_title, API_KEY)
    if "error" in movie_data:
        set_status(status_var, f'Could not load "{movie_title}"')
        messagebox.showerror("Movie Lookup Error", movie_data["error"])
        return

    set_status(status_var, f'Showing details for "{movie_title}"')
    display_movie_info(movie_data, selected)


def display_movie_info(movie_data, movie_record):
    info_window = Toplevel()
    info_window.title(movie_data.get("Title", "Movie Details"))
    info_window.geometry("980x640")
    info_window.configure(bg="#101418")

    container = ttk.Frame(info_window, style="App.TFrame", padding=18)
    container.pack(fill="both", expand=True)
    container.columnconfigure(1, weight=1)
    container.rowconfigure(1, weight=1)

    title_text = movie_data.get("Title", "Movie Details")
    if movie_record.get("watched_at"):
        title_text = f'{title_text}  •  Seen {format_date_label(movie_record["watched_at"])}'

    ttk.Label(
        container,
        text=title_text,
        style="DetailsTitle.TLabel",
    ).grid(row=0, column=0, columnspan=2, sticky="w")

    poster_frame = ttk.Frame(container, style="Card.TFrame", padding=12)
    poster_frame.grid(row=1, column=0, sticky="nsw", padx=(0, 18))

    details_frame = ttk.Frame(container, style="Card.TFrame", padding=12)
    details_frame.grid(row=1, column=1, sticky="nsew")
    details_frame.columnconfigure(0, weight=1)
    details_frame.rowconfigure(0, weight=1)

    text_scroll = Scrollbar(details_frame)
    text_scroll.grid(row=0, column=1, sticky="ns")

    text_info = Text(
        details_frame,
        wrap="word",
        padx=14,
        pady=14,
        font=("Helvetica", 11),
        bg="#fffdf8",
        fg="#1d2730",
        relief="flat",
        yscrollcommand=text_scroll.set,
    )
    text_info.grid(row=0, column=0, sticky="nsew")
    text_info.insert("1.0", format_movie_data(movie_data, movie_record))
    text_info["state"] = "disabled"
    text_scroll.config(command=text_info.yview)

    actions = ttk.Frame(details_frame, style="Card.TFrame")
    actions.grid(row=1, column=0, sticky="w", pady=(12, 0))

    trailer_url = search_youtube_trailer(movie_data.get("Title", ""))
    if trailer_url:
        ttk.Button(
            actions,
            text="Watch Trailer",
            command=lambda: webbrowser.open(trailer_url),
            style="Accent.TButton",
        ).grid(row=0, column=0, sticky="w")

    poster_url = get_tmdb_poster_url(movie_record, movie_data)
    if not poster_url:
        fallback_poster = movie_data.get("Poster", "")
        if fallback_poster and fallback_poster != "N/A":
            poster_url = fallback_poster

    display_poster(poster_frame, poster_url)


def build_styles(root):
    style = ttk.Style(root)
    style.theme_use("clam")

    root.configure(bg="#1f252b")

    style.configure("App.TFrame", background="#1f252b")
    style.configure("Panel.TFrame", background="#2a3138", relief="flat")
    style.configure("Card.TFrame", background="#e8dccd", relief="flat")
    style.configure(
        "Title.TLabel",
        background="#1f252b",
        foreground="#f7f1e8",
        font=("Helvetica", 24, "bold"),
    )
    style.configure(
        "Subtitle.TLabel",
        background="#1f252b",
        foreground="#b9c3cc",
        font=("Helvetica", 11),
    )
    style.configure(
        "Muted.TLabel",
        background="#e8dccd",
        foreground="#4a5560",
        font=("Helvetica", 10),
    )
    style.configure(
        "Panel.TLabel",
        background="#2a3138",
        foreground="#f7f1e8",
        font=("Helvetica", 11),
    )
    style.configure(
        "PanelSubtitle.TLabel",
        background="#2a3138",
        foreground="#c6d0d8",
        font=("Helvetica", 11),
    )
    style.configure(
        "DetailsTitle.TLabel",
        background="#101418",
        foreground="#f7f1e8",
        font=("Helvetica", 20, "bold"),
    )
    style.configure("TLabel", background="#1f252b", foreground="#f7f1e8")
    style.configure(
        "TEntry",
        fieldbackground="#fffdf8",
        foreground="#1d2730",
        padding=8,
        relief="flat",
    )
    style.configure(
        "TButton",
        background="#3e5c76",
        foreground="#f7f1e8",
        padding=(14, 8),
        borderwidth=0,
        focusthickness=0,
    )
    style.map("TButton", background=[("active", "#547b9c")])
    style.configure(
        "Accent.TButton",
        background="#d97757",
        foreground="#fff7f0",
    )
    style.map("Accent.TButton", background=[("active", "#eb8a68")])
    style.configure(
        "TNotebook",
        background="#1f252b",
        borderwidth=0,
        tabmargins=(0, 8, 0, 0),
    )
    style.configure(
        "TNotebook.Tab",
        background="#2a3138",
        foreground="#d8e1e8",
        padding=(16, 10),
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", "#d97757")],
        foreground=[("selected", "#fff7f0")],
    )


def create_listbox(parent):
    listbox = tk.Listbox(
        parent,
        height=14,
        font=("Helvetica", 12),
        bg="#fffdf8",
        fg="#1d2730",
        selectbackground="#d97757",
        selectforeground="#fff7f0",
        activestyle="none",
        bd=0,
        highlightthickness=0,
    )
    listbox.movie_records = []
    return listbox


def setup_main_window():
    root = tk.Tk()
    root.title(APP_TITLE)
    root.geometry("940x700")
    root.minsize(820, 600)
    build_styles(root)

    status_var = tk.StringVar(value="Ready")

    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(1, weight=1)

    header = ttk.Frame(root, style="App.TFrame", padding=(22, 20, 22, 10))
    header.grid(row=0, column=0, sticky="ew")
    header.columnconfigure(0, weight=1)

    ttk.Label(header, text=APP_TITLE, style="Title.TLabel").grid(
        row=0, column=0, sticky="w"
    )
    ttk.Label(
        header,
        text="Track what to watch, mark what you saw, and let old favorites rotate back in.",
        style="Subtitle.TLabel",
    ).grid(row=1, column=0, sticky="w", pady=(4, 0))

    content = ttk.Frame(root, style="App.TFrame", padding=(22, 8, 22, 16))
    content.grid(row=1, column=0, sticky="nsew")
    content.columnconfigure(0, weight=1)
    content.rowconfigure(1, weight=1)

    controls = ttk.Frame(content, style="Panel.TFrame", padding=16)
    controls.grid(row=0, column=0, sticky="ew", pady=(0, 14))
    controls.columnconfigure(0, weight=1)

    ttk.Label(controls, text="Movie Title", style="Panel.TLabel").grid(
        row=0, column=0, sticky="w"
    )
    movie_entry = ttk.Entry(controls)
    movie_entry.grid(row=1, column=0, sticky="ew", pady=(6, 10), padx=(0, 12))

    control_buttons = ttk.Frame(controls, style="Panel.TFrame")
    control_buttons.grid(row=1, column=1, sticky="e", pady=(6, 10))

    notebook = ttk.Notebook(content)
    notebook.grid(row=1, column=0, sticky="nsew")

    watchlist_tab = ttk.Frame(notebook, style="Panel.TFrame", padding=16)
    seen_tab = ttk.Frame(notebook, style="Panel.TFrame", padding=16)
    notebook.add(watchlist_tab, text="Watchlist")
    notebook.add(seen_tab, text="Have Seen")

    for tab in (watchlist_tab, seen_tab):
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)

    ttk.Label(
        watchlist_tab,
        text="Movies still in the running for your next movie night.",
        style="PanelSubtitle.TLabel",
    ).grid(row=0, column=0, sticky="w", pady=(0, 8))
    ttk.Label(
        seen_tab,
        text=f"Recently watched titles stay here for {WATCHED_RETENTION_DAYS} days.",
        style="PanelSubtitle.TLabel",
    ).grid(row=0, column=0, sticky="w", pady=(0, 8))

    watchlist_box = create_listbox(watchlist_tab)
    watchlist_box.grid(row=1, column=0, sticky="nsew")
    watchlist_scroll = ttk.Scrollbar(
        watchlist_tab,
        orient="vertical",
        command=watchlist_box.yview,
    )
    watchlist_scroll.grid(row=1, column=1, sticky="ns")
    watchlist_box.configure(yscrollcommand=watchlist_scroll.set)

    seen_box = create_listbox(seen_tab)
    seen_box.grid(row=1, column=0, sticky="nsew")
    seen_scroll = ttk.Scrollbar(
        seen_tab,
        orient="vertical",
        command=seen_box.yview,
    )
    seen_scroll.grid(row=1, column=1, sticky="ns")
    seen_box.configure(yscrollcommand=seen_scroll.set)

    ttk.Button(
        control_buttons,
        text="Add Movie",
        style="Accent.TButton",
        command=lambda: add_movie(movie_entry, watchlist_box, seen_box, notebook, status_var),
    ).grid(row=0, column=0, padx=(0, 8))
    ttk.Button(
        control_buttons,
        text="Pick For Us",
        command=lambda: pick_random_movie(watchlist_box, status_var),
    ).grid(row=0, column=1)

    watchlist_actions = ttk.Frame(content, style="App.TFrame")
    watchlist_actions.grid(row=2, column=0, sticky="ew", pady=(14, 6))
    for column in range(4):
        watchlist_actions.columnconfigure(column, weight=1)

    ttk.Button(
        watchlist_actions,
        text="Rename Selected",
        command=lambda: edit_movie(
            movie_entry,
            watchlist_box,
            watchlist_box,
            seen_box,
            notebook,
            status_var,
        ),
    ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
    ttk.Button(
        watchlist_actions,
        text="Mark As Seen",
        command=lambda: mark_movie_seen(
            watchlist_box,
            watchlist_box,
            seen_box,
            notebook,
            status_var,
        ),
    ).grid(row=0, column=1, sticky="ew", padx=8)
    ttk.Button(
        watchlist_actions,
        text="Delete Selected",
        command=lambda: delete_movie(
            watchlist_box,
            watchlist_box,
            seen_box,
            notebook,
            status_var,
        ),
    ).grid(row=0, column=2, sticky="ew", padx=8)
    ttk.Button(
        watchlist_actions,
        text="Quit",
        command=root.destroy,
    ).grid(row=0, column=3, sticky="ew", padx=(8, 0))

    seen_actions = ttk.Frame(content, style="App.TFrame")
    seen_actions.grid(row=3, column=0, sticky="ew", pady=(0, 8))
    for column in range(2):
        seen_actions.columnconfigure(column, weight=1)

    ttk.Button(
        seen_actions,
        text="Move Back To Watchlist",
        command=lambda: move_back_to_watchlist(
            seen_box,
            watchlist_box,
            seen_box,
            notebook,
            status_var,
        ),
    ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
    ttk.Button(
        seen_actions,
        text="Delete From Library",
        command=lambda: delete_movie(
            seen_box,
            watchlist_box,
            seen_box,
            notebook,
            status_var,
        ),
    ).grid(row=0, column=1, sticky="ew", padx=(8, 0))

    status_bar = ttk.Label(
        root,
        textvariable=status_var,
        style="Subtitle.TLabel",
        anchor="w",
        padding=(22, 0, 22, 14),
    )
    status_bar.grid(row=2, column=0, sticky="ew")

    watchlist_box.bind(
        "<<ListboxSelect>>",
        lambda event: populate_entry_from_selection(
            event, movie_entry, watchlist_box, seen_box
        ),
    )
    seen_box.bind(
        "<<ListboxSelect>>",
        lambda event: populate_entry_from_selection(
            event, movie_entry, seen_box, watchlist_box
        ),
    )
    watchlist_box.bind(
        "<Double-1>",
        lambda event: on_movie_double_click(event, watchlist_box, status_var),
    )
    seen_box.bind(
        "<Double-1>",
        lambda event: on_movie_double_click(event, seen_box, status_var),
    )
    movie_entry.bind(
        "<Return>",
        lambda event: add_movie(movie_entry, watchlist_box, seen_box, notebook, status_var),
    )
    watchlist_box.bind(
        "<Delete>",
        lambda event: delete_movie(watchlist_box, watchlist_box, seen_box, notebook, status_var),
    )
    seen_box.bind(
        "<Delete>",
        lambda event: delete_movie(seen_box, watchlist_box, seen_box, notebook, status_var),
    )

    refresh_lists(watchlist_box, seen_box, notebook, status_var)
    movie_entry.focus_set()
    root.mainloop()


if __name__ == "__main__":
    initialize_db()
    setup_main_window()
