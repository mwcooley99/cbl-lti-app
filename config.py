import settings
import os
from configparser import ConfigParser


class Config(object):
    PYLTI_CONFIG = settings.PYLTI_CONFIG


class BaseConfig(object):
    DEBUG = False
    TESTING = False
    PYLTI_CONFIG = settings.PYLTI_CONFIG


class DevelopmentConfig(BaseConfig):
    db_pass = os.getenv('DB_PASSWORD')
    username = 'TheDoctor'
    DEBUG = True
    TESTING = True
    PYLTI_CONFIG = settings.PYLTI_CONFIG
    SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{username}:{db_pass}@localhost/cbldb"

class ProductionConfig(BaseConfig):
    db_pass = os.getenv('DB_PASSWORD')
    username = 'TheDoctor'
    DEBUG = False
    TESTING = False
    PYLTI_CONFIG = settings.PYLTI_CONFIG
    SQLALCHEMY_DATABASE_URI = os.getenv('PRODUCTION_DB_URI')


class TestingConfig(BaseConfig):
    DEBUG = False
    TESTING = True
    PYLTI_CONFIG = settings.PYLTI_CONFIG


configuration = {
    'development': DevelopmentConfig,
    'production': ProductionConfig
}