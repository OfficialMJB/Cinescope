import random
import webbrowser
from datetime import date
from io import BytesIO

import tkinter as tk
from tkinter import Canvas, Scrollbar, Text, Toplevel, messagebox, simpledialog, ttk

from database import (
    add_movie_db,
    delete_movie_db,
    expire_seen_movies,
    load_movies,
    mark_movie_seen_db,
    movie_exists,
    reset_movie_to_watchlist_db,
    update_movie_db,
)
from movie_api import (
    fetch_bytes,
    fetch_movie_data,
    format_date_label,
    format_movie_data,
    get_tmdb_poster_url,
    parse_date,
    search_youtube_trailer,
)

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None


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
    movie_data = fetch_movie_data(movie_title)
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
