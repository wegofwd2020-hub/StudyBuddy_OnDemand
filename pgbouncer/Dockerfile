FROM edoburu/pgbouncer:latest

USER root

# Copy the fixed entrypoint script that includes password in database connection string
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

USER postgres
