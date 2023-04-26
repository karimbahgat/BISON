python manage.py migrate
python manage.py process_tasks & 
gunicorn -w 4 -b 0.0.0.0:8000 core.wsgi --timeout 300