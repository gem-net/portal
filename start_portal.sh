#!/usr/bin/env bash

# START PORTAL APP

export LC_ALL=en_US.UTF-8
export LANG=en_US.utf-8


APP_DIR=$(dirname "${BASH_SOURCE}")

source ${APP_DIR}/.env
export FLASK_ENV
export FLASK_APP=${APP_DIR}/app.py

${PY_HOME}/bin/flask run --port 5110
