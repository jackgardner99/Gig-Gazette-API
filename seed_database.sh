#!/bin/bash

rm db.sqlite3
rm -rf ./gigapi/migrations
python3 manage.py migrate
python3 manage.py makemigrations gigapi
python3 manage.py migrate gigapi
python3 manage.py loaddata users
python3 manage.py loaddata tokens
python3 manage.py loaddata artists
