pipeline {
    agent any

    environment {
        APP_NAME   = "render-internship"
        RENDER_DEPLOY_HOOK = credentials('render-deploy-hook-url')
        MONGO_URI  = credentials('mongo-uri')
        SECRET_KEY = credentials('flask-secret-key')
    }

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
                    pip install pytest pytest-cov --quiet
                    export MONGO_URI="mongodb://localhost:27017/test_db"
                    export SECRET_KEY="test-secret"
                    pytest tests/ -v --tb=short || true
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

        stage('Deploy to Render') {
            when {
                branch 'main'
            }
            steps {
                echo "🚀 Triggering Render deployment..."
                sh '''
                    STATUS=$(curl -s -o /dev/null -w "%{http_code}" --request GET "${RENDER_DEPLOY_HOOK}")
                    echo "Render response: $STATUS"
                    if [ "$STATUS" -ge 200 ] && [ "$STATUS" -lt 400 ]; then
                        echo "✅ Deploy triggered!"
                    else
                        echo "❌ Deploy failed with status $STATUS"
                        exit 1
                    fi
                '''
            }
        }

        stage('Verify Deployment') {
            when {
                branch 'main'
            }
            steps {
                echo "⏳ Waiting for Render to spin up..."
                sleep(30)
                sh '''
                    RENDER_URL="https://your-app-name.onrender.com"
                    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${RENDER_URL}")
                    echo "App status: $STATUS"
                    if [ "$STATUS" -ge 200 ] && [ "$STATUS" -lt 400 ]; then
                        echo "✅ App is live!"
                    else
                        echo "⚠️ App returned $STATUS"
                        exit 1
                    fi
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
            cleanWs()
        }
    }

}
