from os import getenv
from app import create_app


FLASK_ENV = getenv('FLASK_ENV', 'production')
app = create_app(FLASK_ENV)
