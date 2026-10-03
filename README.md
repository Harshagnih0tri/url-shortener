# URL Shortener

A small backend service that shortens URLs, redirects to the original URL and tracks clicks.

## 1. Setup and run

Needs Python 3.10+.

```bash
python -m venv venv
venv\Scripts\activate        # on Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
python main.py
```

Or with Docker:

```bash
docker compose up --build
```

The API runs at http://localhost:8000 and interactive docs are at http://localhost:8000/docs.

Run tests:

```bash
pytest
```

Environment variables (all optional):

| Variable | Default |
| --- | --- |
| `PORT` | `8000` |
| `DATABASE_URL` | `sqlite:///./shortener.db` |
| `BASE_URL` | `http://localhost:8000` |
| `RATE_LIMIT` | `10` (creates per minute per IP) |

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/urls` | Create a short URL |
| GET | `/{code}` | Redirect (302), 404 if unknown, 410 if expired |
| GET | `/api/urls/{code}/stats` | Click stats |
| GET | `/api/urls?page=1&limit=20` | List links, newest first |
| DELETE | `/api/urls/{code}` | Delete a link (204) |

Creating links is rate limited (429 if exceeded). All errors return `{"error": "message"}`.

## 2. Stack and why

- Python + FastAPI: I used FastAPI in an earlier project, so I was comfortable with it. It validates request bodies for me and gives free API docs at `/docs`.
- SQLite + SQLAlchemy: no database server to install, so the project runs with one command. Because SQLAlchemy is used, switching to Postgres only needs a different `DATABASE_URL`.
- pytest: simple to write and read tests.

The schema is in `schema.sql`. The app creates the same tables automatically on startup from `models.py`.

## 3. How short codes are generated

Each code is 7 random characters from `a-z A-Z 0-9`, generated with Python's `secrets` module (not `random`, so codes can't be guessed).

There are 62^7 (about 3.5 trillion) possible codes, so collisions are very rare. The `code` column has a UNIQUE constraint. If a new code already exists, the database rejects the insert, I roll back and try again with a new code (up to 5 times).

I rely on the database constraint instead of checking "does this code exist?" first, because two requests at the same time could both pass that check. The constraint can't be bypassed.

Same URL twice: each request gets a new code. This keeps it simple and lets each link have its own expiry and its own click stats.

## 4. Trade-offs and assumptions

- All times are stored and returned in UTC. `clicksByDay` uses UTC dates.
- Clicks on expired links are not counted.
- `expiresAt` in the past is rejected with 400.
- Stats are counted in Python. Fine for this size, but at scale this should be a SQL `GROUP BY`.
- Tables are created with `create_all` instead of a migration tool, to keep the project small.
- No authentication: anyone can create or delete links.
- Rate limiting is kept in memory, so it resets on restart and isn't shared between multiple servers. In production I would use Redis.
- Docker runs only the app. SQLite is a file, so there is no separate database container. The file is kept in a Docker volume.

## 5. Handling 1 million redirects a day

1M a day is about 12 requests per second on average, so the current design is not far off. What I would change:

- Move from SQLite to PostgreSQL, which handles many concurrent writes.
- Add a Redis cache for code-to-URL lookups, since redirects are mostly reads.
- Save clicks in the background (queue + worker) so the redirect doesn't wait for a database write.
- Store daily click counts in a separate table so stats don't scan every click.
- Run multiple app instances behind a load balancer.

## 6. Use of AI tools

I used Claude to help plan the structure and understand concepts. I wrote, ran and tested the code myself.