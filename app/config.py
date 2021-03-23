import os


class BaseConfig:
    ROOTDIR = os.getcwd()

    DEBUG = False

    TESTING = False

    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI')

    SQLALCHEMY_TRACK_MODIFICATIONS = True

    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')

    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')

    GOOGLE_DISCOVERY_URL = 'https://accounts.google.com/.well-known/openid-configuration'

    FACEBOOK_CLIENT_ID = os.getenv('FACEBOOK_CLIENT_ID')

    FACEBOOK_CLIENT_SECRET = os.getenv('FACEBOOK_CLIENT_SECRET')

    REDIS_URL = os.getenv('REDIS_URL')

    SECRET_KEY = os.urandom(32)


class DevelopmentConfig(BaseConfig):
    DEBUG = True

    SECRET_KEY = 'secret'

    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BaseConfig.ROOTDIR, 'db.sqlite3')


class TestingConfig(BaseConfig):
    TESTING = True

    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


class ProductionConfig(BaseConfig):
    ...


def get_config(config_name):
    return {
        'development': DevelopmentConfig,
        'testing': TestingConfig,
        'production': ProductionConfig,
    }.get(config_name)
