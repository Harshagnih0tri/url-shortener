# URL Shortener

A small backend service that turns long URLs into short ones, redirects people to the original URL and keeps track of clicks.

## 1. How to run it

You need Python 3.10 or newer.

```bash
python -m venv venv
venv\Scripts\activate        # on Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
python main.py
```

Or if you have Docker:

```bash
docker compose up --build
```

The app runs on http://localhost:8000. You can try all the endpoints from http://localhost:8000/docs.

To run the tests:

```bash
pytest
```

Settings (all optional, they have defaults):

| Variable | Default |
| --- | --- |
| `PORT` | `8000` |
| `DATABASE_URL` | `sqlite:///./shortener.db` |
| `BASE_URL` | `http://localhost:8000` |
| `RATE_LIMIT` | `10` (links per minute per IP) |

## Endpoints

| Method | Path | What it does |
| --- | --- | --- |
| POST | `/api/urls` | Create a short URL |
| GET | `/{code}` | Redirect (302). 404 if the code doesn't exist, 410 if it has expired |
| GET | `/api/urls/{code}/stats` | Click stats for a link |
| GET | `/api/urls?page=1&limit=20` | List of links, newest first |
| DELETE | `/api/urls/{code}` | Delete a link (204) |

If you create too many links too fast you get a 429. Every error comes back as `{"error": "message"}`.

## 2. Stack and why I picked it

- Python and FastAPI: I used FastAPI in my earlier project, so I already knew it. It checks the request body for me and gives Swagger docs for free.
- SQLite with SQLAlchemy: nothing to install, the database is just a file. Since I used SQLAlchemy, moving to Postgres later only means changing `DATABASE_URL`.
- pytest: easy to write and read.

The tables are in `schema.sql`. The app also creates them by itself when it starts (from `models.py`).

## 3. How the short codes work

Every code is 7 random characters from a-z, A-Z and 0-9. I used Python's `secrets` module instead of `random` so nobody can guess the next code.

That gives 62^7 codes, which is around 3.5 trillion, so two links getting the same code is very unlikely. But it can still happen, so the `code` column is UNIQUE in the database. If the database says the code already exists, I roll back and try again with a new code, up to 5 times.

I didn't do "check if the code exists, then insert", because if two requests come at the same moment, both can pass the check and save the same code. The UNIQUE rule in the database stops that every time.

If someone shortens the same URL twice, they get a new code each time. It keeps the code simple, and each link gets its own expiry and its own stats.

## 4. Trade-offs and assumptions

- All times are in UTC, so `clicksByDay` groups clicks by UTC date.
- If a link is expired, the click is not counted.
- You can't create a link with an expiry date in the past (returns 400).
- Stats are counted in Python. This is fine for a small project, but with a lot of clicks I would count them in SQL with `GROUP BY`.
- Tables are created with `create_all`. In a bigger project I would use migrations (like Alembic).
- There is no login, so anyone can create or delete links. The brief didn't ask for it.
- The rate limit is stored in memory, so it resets when the server restarts. With more than one server I would move it to Redis.
- Docker runs only the app. SQLite is just a file, so it doesn't need its own container. The file is saved in a Docker volume so data is not lost.

## 5. What I would change for 1 million redirects a day

1 million a day is about 12 requests a second on average, so it's not huge. But this is what I would change:

- Switch from SQLite to Postgres, because SQLite isn't good with lots of writes at the same time.
- Add Redis to cache code-to-URL lookups. Most requests are redirects, which only read data, so a cache helps a lot.
- Save clicks in the background (with a queue), so the user doesn't wait for the click to be saved before getting redirected.
- Keep a daily count of clicks in a separate table, so stats don't have to go through every single click.
- Run more than one copy of the app behind a load balancer.

## 6. Did I use AI?

Yes. I used Claude to help me plan the structure, understand things I wasn't sure about (like 302 vs 301 and how to handle code collisions) and review my code. I typed, ran and tested the code myself.