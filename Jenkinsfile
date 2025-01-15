class Globals {
    // the library version
    static String version = 'latest'

    // the default python version
    static String pythonVersion = '3.11'

    // the tag used when publishing documentation
    static String documentationTag = ''

    static final String IMAGE_NAME = 'docker-intern-nexus.meteoswiss.ch/numericalweatherpredictions/fdb-utils-test'
    static final String IMAGE_REPO = 'docker-intern-nexus.meteoswiss.ch'
}

@Library('dev_tools@main') _
pipeline {
    agent {
      podman {
        image 'dockerhub.apps.cp.meteoswiss.ch/mch/python-3.11'
        label 'podman'
      }
    }

    parameters {
        booleanParam(name: 'RELEASE_BUILD', defaultValue: false, description: 'Creates and publishes a new release')
        booleanParam(name: 'PUBLISH_DOCUMENTATION', defaultValue: false, description: 'Publishes the generated documentation')
    }

    environment {
        PROJECT_NAME = 'fdb-utils'

        PIP_USER = 'python-mch'
        SCANNER_HOME = tool name: 'Sonarqube-certs-PROD', type: 'hudson.plugins.sonar.SonarRunnerInstallation';

        HTTP_PROXY = 'http://proxy.meteoswiss.ch:8080'
        HTTPS_PROXY = 'http://proxy.meteoswiss.ch:8080'
        NO_PROXY = '.meteoswiss.ch,localhost'
    }

    options {
        gitLabConnection('CollabGitLab')

        // New jobs should wait until older jobs are finished
        disableConcurrentBuilds()
        // Discard old builds
        buildDiscarder(logRotator(artifactDaysToKeepStr: '7', artifactNumToKeepStr: '1', daysToKeepStr: '45', numToKeepStr: '10'))
        // Timeout the pipeline build after 1 hour
        timeout(time: 1, unit: 'HOURS')
    }

    stages {
        stage('Init') {
            steps {
                updateGitlabCommitStatus name: 'Build', state: 'running'
                script {
                    Globals.documentationTag = env.BRANCH_NAME
                }
            }
        }

        stage('Prepare Test Image') {
            steps {
                withCredentials([usernamePassword(
                                    credentialsId: 'openshift-nexus',
                                    passwordVariable: 'NXPASS', 
                                    usernameVariable: 'NXUSER')
                            ]) {
                    echo "---- BUILDING TEST IMAGE ----"
                    sh """
                    podman build --pull -f Dockerfile -t "${Globals.IMAGE_NAME}:latest" .
                    """
                    echo "---- PUBLISH TEST IMAGE ----"
                    sh """
                    echo $NXPASS | podman login ${Globals.IMAGE_REPO} -u $NXUSER --password-stdin
                    podman push ${Globals.IMAGE_NAME}:latest
                    """
                }
            }
        }

        stage('Test') {
            parallel {
                // python 3.11 is the default version, used for executing pylint, mypy, sphinx etc.
                // all libs. are kept in the .venv folder
                stage('python 3.11') {
                    steps {
                        script {
                            runWithPodman.call "${Globals.IMAGE_NAME}:latest",
                                "poetry install --all-extras && " +
                                "poetry run python -m coverage run --data-file=.coverage -m pytest --junitxml=junit-3.11.xml test/ && " +
                                "poetry run coverage xml"
                        }
                    }
                }
            }
            post {
                always {
                    junit keepLongStdio: true, testResults: 'junit*.xml'
                }
            }
        }

        stage('Run Pylint') {
            steps {
                script {
                    runWithPodman.pythonCmd Globals.pythonVersion,
                        'poetry run pylint -rn --output-format=parseable --output=pylint.log --exit-zero fdb_utils'
                }
            }
        }

        // myPy is treated inside Jenkins because it is not yet integrated with SonarQube (the rest of the CI results is published therein)
        stage('Run Mypy') {
            steps {
                script {
                    runWithPodman.pythonCmd Globals.pythonVersion,
                        'poetry run mypy -p fdb_utils | grep error | tee mypy.log'
                    recordIssues(qualityGates: [[threshold: 10, type: 'TOTAL', unstable: false]], tools: [myPy(pattern: 'mypy.log')])
                }
            }
            post {
                failure {
                    script {
                        error "Too many mypy issues, exiting now..."
                    }
                }
            }
        }

        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv("Sonarqube-PROD") {
                    // fix source path in coverage.xml
                    // (required because coverage is calculated using podman which uses a differing file structure)
                    // https://stackoverflow.com/questions/57220171/sonarqube-client-fails-to-parse-pytest-coverage-results
                    sh "sed -i 's/\\/src\\/app-root/.\\//g' coverage.xml"
                    sh "${SCANNER_HOME}/bin/sonar-scanner"
                }
            }
        }

        stage("Quality Gate") {
            steps {
                timeout(time: 1, unit: 'HOURS') {
                    // Parameter indicates whether to set pipeline to UNSTABLE if Quality Gate fails
                    // true = set pipeline to UNSTABLE, false = don't
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('Release') {
            when { expression { params.RELEASE_BUILD } }
            steps {
                echo 'Build a wheel and publish'
                withCredentials([usernamePassword(
                                    credentialsId: 'github app credential for the meteoswiss github organization (limited to repositories used by APN)',
                                    passwordVariable: 'GITHUB_ACCESS_TOKEN', 
                                    usernameVariable: 'GITHUB_APP')
                            ]) {
                    script {

                        sh "git remote set-url origin https://${GITHUB_APP}:${GITHUB_ACCESS_TOKEN}@github.com/MeteoSwiss/fdb-utils"
                        
                        withCredentials([string(credentialsId: "python-mch-nexus-secret", variable: 'PIP_PWD')]) {
                            runDevScript("build/poetry-lib-release.sh ${env.PIP_USER} $PIP_PWD")
                            Globals.version = sh(script: 'git describe --tags --abbrev=0', returnStdout: true).trim()
                            env.TAG_NAME = Globals.version
                        }
                    }
                }
            }
        }

        stage('Build Documentation') {
            when { expression { params.PUBLISH_DOCUMENTATION } }
            steps {
                script {
                    runWithPodman.pythonCmd Globals.pythonVersion,
                        'poetry install && poetry run sphinx-build doc doc/_build'
                }
            }
        }

        stage('Publish Documentation') {
            when { expression { params.PUBLISH_DOCUMENTATION } }
            environment {
                PATH = "$HOME/tools/openshift-client-tools:$PATH"
                KUBECONFIG = "$workspace/.kube/config"
            }
            steps {
                withCredentials([string(credentialsId: "documentation-main-prod-token", variable: 'TOKEN')]) {
                    sh "oc login https://api.cp.meteoswiss.ch:6443 --token \$TOKEN"
                    publishDoc 'doc/_build/', env.PROJECT_NAME, Globals.version, 'python', Globals.documentationTag
                }
            }
            post {
                cleanup {
                    sh 'oc logout || true'
                }
            }
        }
    }

    post {
        aborted {
            updateGitlabCommitStatus name: 'Build', state: 'canceled'
        }
        failure {
            updateGitlabCommitStatus name: 'Build', state: 'failed'
            echo 'Sending email'
            emailext(subject: "${currentBuild.fullDisplayName}: ${currentBuild.currentResult}",
                attachLog: true,
                attachmentsPattern: 'generatedFile.txt',
                body: "Job '${env.JOB_NAME} #${env.BUILD_NUMBER}': ${env.BUILD_URL}",
                recipientProviders: [requestor(), developers()])
        }
        success {
            echo 'Build succeeded'
            updateGitlabCommitStatus name: 'Build', state: 'success'
        }
        cleanup{
            cleanWs()
        }
    }
}
