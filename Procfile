web: python manage.py migrate && python manage.py seed_data && gunicorn monarch_wealth.wsgi:application --bind 0.0.0.0:$PORT
