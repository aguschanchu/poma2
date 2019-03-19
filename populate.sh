#!/usr/bin/env bash
rm -r slaicer/migrations

#PSQL DB preparation
sudo -u postgres -H -- psql -c "DROP DATABASE poma"
sudo -u postgres -H -- psql -c "CREATE USER poma WITH PASSWORD 'EgCn7f8HMiufkO'"
sudo -u postgres -H -- psql -c "DROP DATABASE poma"
sudo -u postgres -H -- psql -c "CREATE DATABASE poma"
sudo -u postgres -H -- psql -c "ALTER ROLE poma SET client_encoding TO 'utf8'"
sudo -u postgres -H -- psql -c "ALTER ROLE poma SET default_transaction_isolation TO 'read committed'"
sudo -u postgres -H -- psql -c "ALTER ROLE poma SET timezone TO 'UTC'"
sudo -u postgres -H -- psql -c "GRANT ALL PRIVILEGES ON DATABASE poma TO poma"

#DB population
python manage.py makemigrations slaicer
python manage.py makemigrations skynet
python manage.py migrate
#python populate.py
