// Pipeline Starts
pipeline {
    agent any

    triggers {
        cron('0 6 * * *') // Runs every day at 6 AM
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                sh 'pip install -r requirements.txt'
            }
        }

        stage('Run Linting') {
            steps {
                sh 'flake8 automation-tool/'
            }
        }

        stage('Run Multi-Cluster Health Check') {
            steps {
                sh 'python -m runner.cli run configs/pipelines/multi-cluster-health-check.yaml -o reports/'
            }
        }
    }

    post {
        always {
            cleanWs()
        }
    }
}
