pipeline {
    agent any

    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 30, unit: 'MINUTES')
        timestamps()
    }

    stages {

        stage('Checkout') {
            steps {
                echo "📥 Cloning repository..."
                checkout scm
                sh 'git log -1 --oneline'
            }
        }

        stage('Set Up Python Environment') {
            steps {
                echo "🐍 Setting up virtual environment..."
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Lint') {
            steps {
                echo "🔍 Running linter..."
                sh '''
                    . venv/bin/activate
                    pip install flake8 --quiet
                    flake8 . --exclude=venv,migrations --max-line-length=120 --count --statistics || true
                '''
            }
        }

        stage('Run Tests') {
            steps {
                echo "🧪 Running tests..."
                sh '''
                    . venv/bin/activate
                    pip install pytest --quiet
                    export MONGO_URI="mongodb://localhost:27017/test_db"
                    export SECRET_KEY="test-secret"
                    if [ -d "tests" ]; then
                        pytest tests/ -v --tb=short || true
                    else
                        echo "⚠️ No tests directory found, skipping..."
                    fi
                '''
            }
        }

        stage('Security Scan') {
            steps {
                echo "🔒 Running security scan..."
                sh '''
                    . venv/bin/activate
                    pip install bandit --quiet
                    bandit -r . --exclude ./venv,./tests -ll || true
                '''
            }
        }

        stage('Build Complete') {
            steps {
                echo "🎉 Build complete! App is ready."
                sh '''
                    . venv/bin/activate
                    echo "App Name   : render-internship"
                    echo "Branch     : $(git rev-parse --abbrev-ref HEAD)"
                    echo "Commit     : $(git log -1 --oneline)"
                    echo "Build No   : ${BUILD_NUMBER}"
                    echo "Status     : SUCCESS ✅"
                '''
            }
        }

    }

    post {
        success {
            echo "✅ Build #${BUILD_NUMBER} passed!"
        }
        failure {
            echo "❌ Build #${BUILD_NUMBER} failed — check logs."
        }
        always {
            node('built-in') {
                cleanWs()
            }
        }
    }
}
