#!/usr/bin/env bash

echo "Remember to install and run rabbitmq-server before starting the celery instance"
celery purge -f -A poma2
celery -A poma2 worker -B -E -l info
