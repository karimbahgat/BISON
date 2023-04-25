python manage.py migrate
python manage.py loaddata AdminSource.json DatasetImporter.json
python manage.py process_tasks & 
gunicorn -w 3 -b 0.0.0.0:8000 core.wsgi --timeout 300