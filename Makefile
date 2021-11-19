include .env
export
ROOT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

init:
	pip install -r requirements.txt

test:
	pytest

coverage:
	 pytest --cov=jericho --cov-report=xml

analyze:
	docker run \
    --rm \
    -e SONAR_HOST_URL="http://localhost:9000" \
    -e SONAR_LOGIN="${SONARQUBE_API}" \
    -v "${ROOT_DIR}:/usr/src" \
    --net="host" \
    sonarsource/sonar-scanner-cli '-Dsonar.projectKey=jericho' '-Dsonar.exclusions=tests/assets/*,tests/*,jericho/enums/*,jericho/jericho.py' -D'sonar.python.coverage.reportPaths=coverage.xml' -D'sonar.python.version=3.8.10' -D'sonar.core.codeCoveragePlugin=pytest'