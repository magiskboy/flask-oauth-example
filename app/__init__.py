from flask import Flask
from werkzeug.exceptions import HTTPException

from .config import get_config
from .models import init_app as init_db
from .auth import init_app as init_auth, bp as auth_bp
from .post import bp as post_bp


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    init_db(app)
    init_auth(app)

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(post_bp, url_prefix='/posts')

    @app.route('/health')
    def health():       #pylint:disable=W0612
        return '', 204

    @app.errorhandler(HTTPException)
    def handle_error(e):    #pylint:disable=W0612
        return {
            'message': e.description,
            'name': e.name
        }, e.code

    return app
