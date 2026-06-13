release: python manage.py migrate
web: gunicorn gigproject.wsgi --bind 0.0.0.0:$PORT
