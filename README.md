# URL Shortener

A small backend service that turns long URLs into short ones, redirects people to the original URL and keeps track of clicks.

## 1. How to run it

You need Python 3.10 or newer.

```bash
python -m venv venv
venv\Scripts\activate             # Windows
source venv/bin/activate          # Mac/Linux
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

- Python and FastAPI: I used FastAPI in my GrowthX project (a habit tracker backend), so I already knew it. It checks the request body for me and gives Swagger docs for free.
- SQLite with SQLAlchemy: nothing to install, the database is just a file. Since I used SQLAlchemy, moving to Postgres later only means changing `DATABASE_URL`.
- pytest: easy to write and read.

The tables are in `schema.sql`. The app also creates them by itself when it starts (from `models.py`).

## 3. How the short codes work

I generate a 7-character code using `secrets` (letters and numbers). There are so many possible codes that collisions should be rare, but I still keep a UNIQUE constraint on the `code` column as a safety check. If a collision happens, the app rolls back and tries a new code, up to 5 times.

I let the database catch duplicates instead of checking first, because two requests at the same time could both pass a check.

If someone shortens the same URL twice, they get a new code each time, so each link has its own expiry and stats.

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

That's around 12 requests a second, so it's not a lot, but I would:

- Move from SQLite to Postgres.
- Cache code-to-URL lookups in Redis, since most requests are redirects.
- Save clicks in the background so redirects stay fast.
- Run more than one instance of the app behind a load balancer.

## 6. Did I use AI?

Yes. I used Claude to help me plan the structure, understand things I wasn't sure about (like 302 vs 301 and how to handle code collisions) and review my code. I typed, ran and tested the code myself.