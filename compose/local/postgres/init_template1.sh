#!/bin/bash
set -e

# Enable PostGIS in template1 so any new databases (e.g. Django test databases) automatically inherit it
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "template1" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS postgis;
EOSQL
