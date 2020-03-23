import os

import app.settings as settings


class Config(object):
    PYLTI_CONFIG = settings.PYLTI_CONFIG


class BaseConfig(object):
    DEBUG = False
    TESTING = False
    PYLTI_CONFIG = settings.PYLTI_CONFIG


class DevelopmentConfig(BaseConfig):
    db_pass = os.getenv('DB_PASSWORD')
    username = 'TheDoctor'
    SECRET_KEY = os.getenv('SECRET_FLASK')
    DEBUG = True
    TESTING = True
    PYLTI_CONFIG = settings.PYLTI_CONFIG
    SQLALCHEMY_DATABASE_URI = os.getenv('DEVELOPMENT_DB_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = True


class StageConfig(BaseConfig):
    db_pass = os.getenv('DB_PASSWORD')
    username = 'TheDoctor'
    SECRET_KEY = os.getenv('SECRET_FLASK')
    DEBUG = False
    TESTING = False
    PYLTI_CONFIG = settings.PYLTI_CONFIG
    SQLALCHEMY_DATABASE_URI = os.getenv('STAGE_DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True


class ProductionConfig(BaseConfig):
    db_pass = os.getenv('DB_PASSWORD')
    username = 'TheDoctor'
    SECRET_KEY = os.getenv('SECRET_FLASK')
    DEBUG = False
    TESTING = False
    PYLTI_CONFIG = settings.PYLTI_CONFIG
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'None'


class TestingConfig(BaseConfig):
    DEBUG = False
    TESTING = True
    PYLTI_CONFIG = settings.PYLTI_CONFIG


configuration = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'stage': StageConfig
}
