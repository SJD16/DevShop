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
    }
}
