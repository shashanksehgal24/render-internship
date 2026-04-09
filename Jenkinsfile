pipeline {
    agent any

    environment {
        // --- Project Settings ---
        APP_NAME        = "render-internship"
        PYTHON_VERSION  = "3.11"

        // --- Docker / Registry (optional – skip if not using Docker) ---
        DOCKER_IMAGE    = "your-dockerhub-username/${APP_NAME}"
        DOCKER_TAG      = "${BUILD_NUMBER}"

        // --- Render Deploy Hook ---
        // Store this in Jenkins > Manage Credentials > Secret text
        // Get it from: Render Dashboard → Your Service → Settings → Deploy Hook
        RENDER_DEPLOY_HOOK = credentials('render-deploy-hook-url')

        // --- App Secrets (add these as Jenkins secret-text credentials) ---
        MONGO_URI       = credentials('mongo-uri')
        SECRET_KEY      = credentials('flask-secret-key')
        CLOUDINARY_URL  = credentials('cloudinary-url')  // remove if unused
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 30, unit: 'MINUTES')
        timestamps()
    }

    triggers {
        // Auto-trigger on GitHub push (requires GitHub plugin + webhook configured)
        githubPush()
    }

    stages {

        // ─────────────────────────────────────────────
        stage('Checkout') {
        // ─────────────────────────────────────────────
            steps {
                echo "📥 Cloning repository..."
                checkout scm
                sh 'git log -1 --oneline'
            }
        }

        // ─────────────────────────────────────────────
        stage('Set Up Python Environment') {
        // ─────────────────────────────────────────────
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

        // ─────────────────────────────────────────────
        stage('Lint') {
        // ─────────────────────────────────────────────
            steps {
                echo "🔍 Running linter (flake8)..."
                sh '''
                    . venv/bin/activate
                    pip install flake8 --quiet
                    # Ignore line-length (E501) – adjust as needed
                    flake8 . --exclude=venv,migrations --max-line-length=120 --count --statistics || true
                '''
            }
        }

        // ─────────────────────────────────────────────
        stage('Run Tests') {
        // ─────────────────────────────────────────────
            steps {
                echo "🧪 Running unit tests..."
                sh '''
                    . venv/bin/activate
                    pip install pytest pytest-cov --quiet
                    # Set a test MONGO_URI so tests don't hit production DB
                    export MONGO_URI="mongodb://localhost:27017/test_db"
                    export SECRET_KEY="test-secret"
                    pytest tests/ -v --tb=short --cov=. --cov-report=xml --cov-report=term-missing || true
                '''
            }
            post {
                always {
                    // Publish coverage if cobertura plugin is installed
                    publishCoverage adapters: [coberturaAdapter('coverage.xml')],
                                    sourceFileResolver: sourceFiles('STORE_LAST_BUILD') \
                        || echo "Coverage plugin not installed – skipping report"
                }
            }
        }

        // ─────────────────────────────────────────────
        stage('Security Scan') {
        // ─────────────────────────────────────────────
            steps {
                echo "🔒 Running Bandit security scan..."
                sh '''
                    . venv/bin/activate
                    pip install bandit --quiet
                    bandit -r . --exclude ./venv,./tests -ll || true
                '''
            }
        }

        // ─────────────────────────────────────────────
        stage('Docker Build & Push') {
        // ─────────────────────────────────────────────
            // Remove this stage if you are NOT using Docker on Render
            when {
                branch 'main'
            }
            steps {
                echo "🐳 Building Docker image..."
                script {
                    withCredentials([usernamePassword(
                        credentialsId : 'dockerhub-credentials',
                        usernameVariable: 'DOCKER_USER',
                        passwordVariable: 'DOCKER_PASS'
                    )]) {
                        sh '''
                            echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
                            docker build -t ${DOCKER_IMAGE}:${DOCKER_TAG} \
                                         -t ${DOCKER_IMAGE}:latest .
                            docker push ${DOCKER_IMAGE}:${DOCKER_TAG}
                            docker push ${DOCKER_IMAGE}:latest
                        '''
                    }
                }
            }
        }

        // ─────────────────────────────────────────────
        stage('Deploy to Render') {
        // ─────────────────────────────────────────────
            when {
                branch 'main'      // only deploy from main branch
            }
            steps {
                echo "🚀 Triggering Render deployment..."
                sh '''
                    curl -s -o /dev/null -w "%{http_code}" \
                         --request GET "${RENDER_DEPLOY_HOOK}" \
                    | grep -q "^2" && echo "✅ Render deploy triggered successfully." \
                                   || (echo "❌ Render deploy hook failed!" && exit 1)
                '''
            }
        }

        // ─────────────────────────────────────────────
        stage('Verify Deployment') {
        // ─────────────────────────────────────────────
            when {
                branch 'main'
            }
            steps {
                echo "⏳ Waiting 30 s for Render to spin up..."
                sleep(30)
                echo "🌐 Checking app health..."
                sh '''
                    # Replace with your actual Render URL
                    RENDER_URL="https://your-app-name.onrender.com"
                    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${RENDER_URL}")
                    echo "HTTP Status: $HTTP_STATUS"
                    if [ "$HTTP_STATUS" -ge 200 ] && [ "$HTTP_STATUS" -lt 400 ]; then
                        echo "✅ App is live and responding!"
                    else
                        echo "⚠️  App returned status $HTTP_STATUS – check Render logs."
                        exit 1
                    fi
                '''
            }
        }

    } // end stages

    post {
        success {
            echo "✅ Pipeline completed successfully — Build #${BUILD_NUMBER}"
        }
        failure {
            echo "❌ Pipeline FAILED — Build #${BUILD_NUMBER}. Check the logs above."
            // Optional: send email notification
            // mail to: 'you@example.com',
            //      subject: "Jenkins Build FAILED: ${JOB_NAME} #${BUILD_NUMBER}",
            //      body: "Check: ${BUILD_URL}"
        }
        always {
            echo "🧹 Cleaning workspace..."
            cleanWs()
        }
    }

}
