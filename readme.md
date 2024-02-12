## Telegram bot with django backend

### get started:

to run **django server** use command: `python manage.py runserver`

if there are problems with migrations then run:
- `python manage.py makemigrations`
- `python manage.py migrate`

run **telegram bot** with command:
`python bot.py`

### other:

admin view can be found on [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin)

admin view most likely requires you to create a superuser with command:

`python manage.py createsuperuser`

### files:

you need `config.py` file with values **TOKEN** and **SECRET_KEY**