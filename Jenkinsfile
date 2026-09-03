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
                    docker network create devshop-ci-network || true

                    docker rm -f devshop-postgres 2>/dev/null || true

                    docker run -d \
                        --name devshop-postgres \
                        --network devshop-ci-network \
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
                    DATABASE_URL=postgresql+psycopg://devshop:devshop_ci_password@localhost:5432/devshop_test \
                    .venv/bin/alembic upgrade head
                '''
            }
        }
        stage('Run Tests') {
            steps {
                sh '''
                    export DATABASE_URL="postgresql+psycopg://devshop:devshop_ci_password@localhost:5432/devshop_test"
                    export TEST_DATABASE_URL="postgresql+psycopg://devshop:devshop_ci_password@localhost:5432/devshop_test"
                    export JWT_SECRET_KEY="devshop-ci-test-secret-0000000000000000000000000000000000000000000000000000000000000000"

                    .venv/bin/pytest -q
                '''
            }
        }
        stage('Build Docker Image') {
            steps {
                sh 'docker build -t devshop:${BUILD_NUMBER} .'
            }
        }
        stage('Validate Docker Image') {
            steps {
                sh '''
                    docker rm -f devshop-app-ci || true

                    docker run -d \
                    --name devshop-app-ci \
                    --network devshop-ci-network \
                    -p 8000:8000 \
                    -e DATABASE_URL="postgresql+psycopg://devshop:devshop_ci_password@devshop-postgres:5432/devshop_test" \
                    -e JWT_SECRET_KEY="devshop-ci-test-secret-0000000000000000000000000000000000000000000000000000000000000000" \
                    devshop:${BUILD_NUMBER}

                    echo "Waiting for DevShop container..."

                    for i in $(seq 1 30); do
                        if curl -fsS http://localhost:8000/; then
                            echo
                            echo "DevShop container is healthy"
                            break
                        fi

                        echo "DevShop not ready yet (attempt $i/30)"
                        sleep 2
                    done

                    curl -fsS http://localhost:8000/

                    docker rm -f devshop-app-ci
                '''
            }
        }
        stage('Push Docker Image') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'dockerhub-creds',
                        usernameVariable: 'DOCKER_USERNAME',
                        passwordVariable: 'DOCKER_PASSWORD'
                    )
                ]) {
                    sh '''
                        echo "$DOCKER_PASSWORD" | docker login \
                            -u "$DOCKER_USERNAME" \
                            --password-stdin

                        docker tag devshop:${BUILD_NUMBER} \
                            ${DOCKER_USERNAME}/devshop:${BUILD_NUMBER}

                        docker push ${DOCKER_USERNAME}/devshop:${BUILD_NUMBER}

                        docker logout
                    '''
                }
            }
        }
    }
}
