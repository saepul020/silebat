#!/bin/sh

set -e

echo "Menunggu database PostgreSQL siap..."

until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; do
  sleep 1
done

echo "Database siap."

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"