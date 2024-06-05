#!/bin/sh

until cd /app/lmming
do
    echo "Waiting for server volume..."
done

#echo "Waiting for postgres..."
#while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
#    sleep 0.1
#done
#echo "PostgreSQL started"

until python manage.py migrate
do
    echo "Waiting for db to be ready..."
    sleep 2
done


python manage.py collectstatic --noinput

# python manage.py createsuperuser --noinput

gunicorn lmming.wsgi --bind 0.0.0.0:8000 --workers 4 --threads 4