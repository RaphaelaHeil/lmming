FROM python:3.10.14-slim-bookworm

RUN apt-get update && apt-get -y upgrade
RUN apt-get -y install python3-dev gcc libc-dev postgresql-client


WORKDIR /app

RUN pip install --upgrade pip
RUN pip install gunicorn
ADD ./requirements.txt /app/
RUN pip install -r requirements.txt
RUN pip install psycopg2-binary

ADD ./lmming /app/lmming
ADD ./docker /app/docker

RUN chmod +x /app/docker/lmming/server-entrypoint.sh
RUN chmod +x /app/docker/lmming/worker-entrypoint.sh