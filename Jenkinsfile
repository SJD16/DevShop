pipeline {
    agent any

    stages {
        stage('Hello') {
            steps {
                echo 'DevShop CI pipeline starting...'
            }
        }

        stage('Environment') {
            steps {
                sh 'python3 --version'
                sh 'pip3 --version'
            }
        }
    }
}
