#!/bin/sh

until cd /app/lmming
do
    echo "Waiting for server volume..."
done

celery -A lmming worker -l info -P solo
