
# CineScope

CineScope is a desktop movie tracker built with Tkinter and SQLite.

It lets you:
- keep a watchlist
- mark movies as seen with the date you watched them
- move older watched movies back into the watchlist after about 6 months
- pick a random movie for movie night
- open trailers and poster art from movie detail screens

## Features

- OMDb is used for movie details like plot, ratings, cast, and runtime.
- TMDb is used for poster lookups.
- YouTube search is used for trailer links.
- SQLite stores your movie list locally in `movies.db`.

## Project Files

- `CineScope.py`: main Tkinter application
- `movies.db`: local database for your movie library

## Requirements

- Python 3.9+
- Pillow for poster rendering inside the app

Install Pillow into the same Python you use to launch the app:

```bash
/usr/local/bin/python3 -m pip install --upgrade pillow
```

## API Keys

CineScope currently supports:
- `OMDB_API_KEY`
- `TMDB_API_KEY`
- `YOUTUBE_API_KEY`

Set them in your shell before launching:

```bash
export OMDB_API_KEY='your_omdb_key'
export TMDB_API_KEY='your_tmdb_key'
export YOUTUBE_API_KEY='your_youtube_key'
```

Then run:

```bash
/usr/local/bin/python3 /Users/michaelbenavides/Desktop/Cinescope/CineScope.py
```

If you do not set a TMDb key, movie detail pages may still load, but poster support will be limited.

## How It Works

### Watchlist

Add movies you want to watch.

Use:
- `Add Movie` to save a title
- `Rename Selected` to clean up a title
- `Delete Selected` to remove it
- `Pick For Us` to choose a random movie from the watchlist

### Have Seen

When you watch a movie:
1. Select it in the watchlist
2. Click `Mark As Seen`
3. Enter the date you watched it in `YYYY-MM-DD` format

The movie then moves into the `Have Seen` tab.

After 180 days, CineScope automatically moves it back into the watchlist so it can come up again later.

You can also manually send a watched movie back with `Move Back To Watchlist`.

## Database Notes

The app uses `movies.db` in the same folder as `CineScope.py`.

The app now stores:
- movie title
- watched date
- cached TMDb poster path

Your existing database is migrated automatically when the app starts.

## Troubleshooting

### Posters are not showing

Check these first:
- `TMDB_API_KEY` is set in the shell where you launch the app
- Pillow is installed in the same Python environment as the app
- your internet connection is working

Test Pillow with:

```bash
/usr/local/bin/python3 -c "from PIL import Image, ImageTk; print('Pillow OK')"
```

### Module not found

Install packages with the same interpreter you use to launch the app:

```bash
/usr/local/bin/python3 -m pip install --upgrade pillow
```

### Movie details fail to load

That usually means:
- the OMDb request failed
- the movie title needs to be cleaned up
- the API key is invalid or missing

## Future Ideas

- add notes or personal ratings
- add genre filters for random picks
- add a "watched with" tag
- add import/export to JSON or CSV
- add a poster grid view
>>>>>>> 90cb7e1 (Initial commit.)
