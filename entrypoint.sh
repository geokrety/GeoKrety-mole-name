#!/bin/sh

/opt/flask/create-database.py

exec "$@"
