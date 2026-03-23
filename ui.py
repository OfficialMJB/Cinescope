from tkinter import ttk

from ui_actions import (
    add_movie,
    delete_movie,
    edit_movie,
    mark_movie_seen,
    move_back_to_watchlist,
    on_movie_double_click,
    pick_random_movie,
    populate_entry_from_selection,
    refresh_lists,
)
from ui_views import build_main_window


def setup_main_window():
    widgets = build_main_window()
    root = widgets["root"]
    status_var = widgets["status_var"]
    movie_entry = widgets["movie_entry"]
    control_buttons = widgets["control_buttons"]
    notebook = widgets["notebook"]
    watchlist_box = widgets["watchlist_box"]
    seen_box = widgets["seen_box"]
    watchlist_actions = widgets["watchlist_actions"]
    seen_actions = widgets["seen_actions"]

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
