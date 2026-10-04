# Local Development

This guide runs the FastAPI application on a developer machine with PostgreSQL. It does not provision or deploy AWS resources.

## Prerequisites

- Python 3.12, Git, and Docker (if using the PostgreSQL container or application image).
- A PostgreSQL server reachable from the development environment.
- A shell appropriate to your operating system; commands below show POSIX shell and PowerShell alternatives where activation differs.

## Python environment and dependencies

From the repository root, create and activate a virtual environment, then install the pinned project dependencies:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

In PowerShell, activate with `.\.venv\Scripts\Activate.ps1` after `py -3.12 -m venv .venv`.

## PostgreSQL and environment configuration

The application reads `DATABASE_URL` and `JWT_SECRET_KEY` from the process environment (and calls `load_dotenv`). Copy `.env.example` to `.env`, then set a local-only random JWT signing key and a database URL that matches your local PostgreSQL user, password, host, port, and database. Do not reuse production credentials or commit `.env`.

For example, a disposable local database can be started with Docker:

```sh
docker run --name devshop-postgres \
  -e POSTGRES_USER=devshop \
  -e POSTGRES_PASSWORD=local-only-password \
  -e POSTGRES_DB=devshop \
  -p 5432:5432 -d postgres:16
```

Set `DATABASE_URL` to the matching `postgresql+psycopg://...` URL. Tests use `TEST_DATABASE_URL`; by default, `tests/conftest.py` points it at a separate local `devshop_test` database. Create that database and set the URL explicitly before testing. The test fixture truncates application tables, so never point it at a database containing data you need to keep.

## Alembic migrations

Apply the checked-in migrations to the database selected by `DATABASE_URL`:

```sh
alembic upgrade head
```

To see the current migration revision:

```sh
alembic current
```

## Run the FastAPI application

With the environment configured and the development database migrated:

```sh
uvicorn app.main:app --reload
```

The local server listens on `http://127.0.0.1:8000`. The root endpoint returns a small status response. API routes are defined under `app/api/`.

## Run tests

Configure `TEST_DATABASE_URL` for a separate PostgreSQL test database, migrate that same database, then run:

```sh
export DATABASE_URL="$TEST_DATABASE_URL"
alembic upgrade head
pytest -q
```

The suite uses a live PostgreSQL database and clears the application tables around tests. It is not a SQLite-only test setup.

## Docker

Build the application image from the repository root:

```sh
docker build -t devshop:local .
```

The Dockerfile exposes port 8000 and starts Uvicorn. The container still needs valid `DATABASE_URL` and `JWT_SECRET_KEY` values and a reachable PostgreSQL service. For example, attach it to the network of a local PostgreSQL container and provide those environment variables at `docker run` time. Do not bake credentials into the image.

## Useful checks

```sh
python --version
python -m pip check
alembic current
pytest -q
curl http://127.0.0.1:8000/
```

For AWS EKS deployment and verification, use the [AWS deployment guide](aws-deployment.md) and [EKS rebuild runbook](../runbooks/rebuild-eks.md).
