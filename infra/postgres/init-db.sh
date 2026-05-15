#!/bin/bash
set -e

# Create the additional database if it doesn't exist
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" <<-EOSQL
  SELECT 'CREATE DATABASE assetops'
  WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'assetops')\gexec
EOSQL
