import tkinter as tk
from tkinter import ttk

from config import APP_TITLE, WATCHED_RETENTION_DAYS


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


def build_main_window():
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

    watchlist_actions = ttk.Frame(content, style="App.TFrame")
    watchlist_actions.grid(row=2, column=0, sticky="ew", pady=(14, 6))
    for column in range(4):
        watchlist_actions.columnconfigure(column, weight=1)

    seen_actions = ttk.Frame(content, style="App.TFrame")
    seen_actions.grid(row=3, column=0, sticky="ew", pady=(0, 8))
    for column in range(2):
        seen_actions.columnconfigure(column, weight=1)

    status_bar = ttk.Label(
        root,
        textvariable=status_var,
        style="Subtitle.TLabel",
        anchor="w",
        padding=(22, 0, 22, 14),
    )
    status_bar.grid(row=2, column=0, sticky="ew")

    return {
        "root": root,
        "status_var": status_var,
        "movie_entry": movie_entry,
        "control_buttons": control_buttons,
        "notebook": notebook,
        "watchlist_box": watchlist_box,
        "seen_box": seen_box,
        "watchlist_actions": watchlist_actions,
        "seen_actions": seen_actions,
        "status_bar": status_bar,
    }
