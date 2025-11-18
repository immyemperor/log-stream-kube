#!/bin/sh

set -e
# Function to check database availability
wait_for_postgres() {
    # Extract database connection details from environment variables or application configuration
    # Assuming standard PostgreSQL env vars are used (PGHOST, PGPORT, PGUSER, PGDATABASE)
    echo "Waiting for PostgreSQL to become available..."

    while ! pg_isready -h "$POSTGRES_HOST" -U "$POSTGRES_USER" > /dev/null 2>&1; do
        sleep 1
    done

    echo "PostgreSQL is available. Running migrations..."
}

# Wait for the database
wait_for_postgres
# gunicorn 'app:create_app()'
export FLASK_APP=app:create_app

flask db upgrade

echo "Migrations complete."
exec "$@"