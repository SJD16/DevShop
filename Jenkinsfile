pipeline {
    agent any
    options {
            disableConcurrentBuilds()
        }
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
                    echo "PAUSING FOR RACE CONDITION TEST..."
                    sleep 60
                '''
            }
        }
        stage('Build Docker Image') {
            steps {
                script {
                    env.IMAGE_TAG = sh(
                        script: 'git rev-parse --short HEAD',
                        returnStdout: true
                    ).trim()

                    env.SOURCE_COMMIT = sh(
                        script: 'git rev-parse HEAD',
                        returnStdout: true
                    ).trim()

                    echo "IMAGE_TAG=${env.IMAGE_TAG}"
                    echo "SOURCE_COMMIT=${env.SOURCE_COMMIT}"
                }

                sh '''
                    echo "Building Docker image:"
                    echo "devshop:${IMAGE_TAG}"

                    docker build -t devshop:${IMAGE_TAG} .
                '''
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
                        devshop:${IMAGE_TAG}

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

                        docker tag devshop:${IMAGE_TAG} \
                            ${DOCKER_USERNAME}/devshop:${IMAGE_TAG}

                        docker push ${DOCKER_USERNAME}/devshop:${IMAGE_TAG}

                        docker logout
                    '''
                }
            }
        }

        stage('Update Kubernetes Image') {
            steps {
                sh '''
                    sed -i "s|image: sjd16/devshop:.*|image: sjd16/devshop:${IMAGE_TAG}|" k8s/devshop.yaml

                    echo "Updated Kubernetes manifest:"
                    grep "image:" k8s/devshop.yaml

                    echo
                    echo "Verifying Kubernetes image..."

                    if ! grep -q "image: sjd16/devshop:${IMAGE_TAG}" k8s/devshop.yaml; then
                        echo "ERROR: Kubernetes manifest does not contain expected image:"
                        echo "sjd16/devshop:${IMAGE_TAG}"
                        exit 1
                    fi

                    echo "Kubernetes manifest contains the expected image:"
                    echo "sjd16/devshop:${IMAGE_TAG}"

                    echo
                    echo "Git diff:"
                    git diff -- k8s/devshop.yaml
                '''
            }
        }

        stage('Commit Kubernetes Image Update') {
            steps {
                script {
                    sh '''
                        git config user.name "Jenkins"
                        git config user.email "jenkins@devshop.local"

                        git add k8s/devshop.yaml

                        echo "Checking for Kubernetes manifest changes..."

                        if git diff --cached --quiet -- k8s/devshop.yaml; then
                            echo "No Kubernetes manifest changes detected."
                            echo "Image tag is already ${IMAGE_TAG}."
                        else
                            echo "Kubernetes manifest has changed."
                            echo "Committing image update..."

                            echo
                            echo "Staged changes:"
                            git diff --cached -- k8s/devshop.yaml

                            git commit -m "Update DevShop image to ${IMAGE_TAG}"

                            echo "Kubernetes manifest commit created."
                        fi
                    '''
                }
            }
        }


        stage('Push Kubernetes Manifest Update') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'github-push',
                        usernameVariable: 'GIT_USERNAME',
                        passwordVariable: 'GIT_PASSWORD'
                    )
                ]) {
                    sh '''
                        echo "Fetching latest origin/master..."

                        git fetch origin master

                        REMOTE_MASTER=$(git rev-parse origin/master)

                        echo "Jenkins source commit:"
                        echo "${SOURCE_COMMIT}"

                        echo "Current origin/master:"
                        echo "${REMOTE_MASTER}"

                        if [ "${REMOTE_MASTER}" != "${SOURCE_COMMIT}" ]; then
                            echo
                            echo "ERROR: origin/master changed during this Jenkins build."
                            echo "Jenkins started from:"
                            echo "${SOURCE_COMMIT}"
                            echo "But origin/master is now:"
                            echo "${REMOTE_MASTER}"
                            echo
                            echo "Refusing to push in order to avoid overwriting"
                            echo "another Git commit."
                            exit 1
                        fi

                        echo "origin/master has not changed."
                        echo "Safe to push Jenkins GitOps commit."

                        git push https://${GIT_USERNAME}:${GIT_PASSWORD}@github.com/SJD16/DevShop.git HEAD:master
                    '''
                }
            }
        }                
    }
    post {
        always {
            sh '''
                echo "Cleaning up CI Docker resources..."

                docker rm -f devshop-app-ci 2>/dev/null || true
                docker rm -f devshop-postgres 2>/dev/null || true

                docker network rm devshop-ci-network 2>/dev/null || true

                echo "CI Docker cleanup complete."
            '''
        }
    }
}
