# Postgres Notes

## Starting a Postgres Docker Container

```
docker run -itd -e POSTGRES_USER=<username> -e POSTGRES_PASSWORD=<password> -p 5432:5432 -v /data:/var/lib/postgresql/data --name <container-name> postgres
```

## Connecting to Postgres via psql

```
PGPASSWORD=<password> psql -U <username> -h localhost -p 5432
```

## Setting up pgAdmin in Docker
```
docker run --name <container-name> -p 5051:80 -e "PGADMIN_DEFAULT_EMAIL=<admin-email>" -e "PGADMIN_DEFAULT_PASSWORD=<admin-password>" -d dpage/pgadmin4
```

- admin-email is needed to log into pgadmin
- in order to connect to the DB within the other docker container, use:
  - host name/address = host.docker.internal
  - username = <username>
  - password = <password>

--> same as for psql, except for the **host**! 