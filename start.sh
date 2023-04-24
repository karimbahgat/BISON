python manage.py migrate
python manage.py loaddata AdminSource.json DatasetImporter.json
gunicorn -w 2 -b 0.0.0.0:8000 core.wsgi --timeout 300