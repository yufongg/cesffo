#!/bin/bash
set -e

# assign environment variable to psql
# psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
#     -- Create the non-root user using the env variable
#     CREATE USER "$APP_USER" WITH PASSWORD '$APP_PASSWORD';

#     -- Grant permissions dynamically
#     GRANT ALL PRIVILEGES ON DATABASE $POSTGRES_DB TO "$APP_USER";
    
#     \c $POSTGRES_DB
#     GRANT ALL ON SCHEMA public TO "$APP_USER";
# EOSQL