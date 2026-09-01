pipeline {
    agent any

    stages {

        stage('Hello') {
            steps {
                echo 'DevShop CI pipeline starting...'
            }
        }

        stage('Python Environment') {
            steps {
                sh '''
                    python3 --version
                    python3 -m venv .venv
                    .venv/bin/python --version
                    .venv/bin/pip --version
                '''
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '''
                    .venv/bin/python -m pip install --upgrade pip
                    .venv/bin/python -m pip install -r requirements.txt
                    .venv/bin/python -m pip freeze
                '''
            }
        }

        stage('Start PostgreSQL') {
            steps {
                sh '''
                    docker rm -f devshop-postgres 2>/dev/null || true

                    docker run -d \
                        --name devshop-postgres \
                        -e POSTGRES_USER=devshop \
                        -e POSTGRES_PASSWORD=devshop_ci_password \
                        -e POSTGRES_DB=devshop_test \
                        -p 5432:5432 \
                        postgres:16
                '''
            }
        }

        stage('Verify PostgreSQL') {
            steps {
                sh '''
                    .venv/bin/python - <<'PY'
import time
import psycopg

for attempt in range(30):
    try:
        conn = psycopg.connect(
            "postgresql://devshop:devshop_ci_password@localhost:5432/devshop_test"
        )
        conn.close()
        print("PostgreSQL is ready")
        break
    except psycopg.OperationalError:
        print(f"PostgreSQL not ready yet (attempt {attempt + 1}/30)")
        time.sleep(1)
else:
    raise RuntimeError("PostgreSQL did not become ready")
PY
                '''
            }
        }
        stage('Run Database Migrations') {
            steps {
                sh '''
                    DATABASE_URL="postgresql://devshop:devshop_ci_password@localhost:5432/devshop_test" \
                    .venv/bin/alembic upgrade head
                '''
            }
        }
    }
}
