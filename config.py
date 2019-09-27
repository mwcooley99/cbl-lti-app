import settings


class Config(object):
    PYLTI_CONFIG = settings.PYLTI_CONFIG


class BaseConfig(object):
    DEBUG = False
    TESTING = False
    PYLTI_CONFIG = settings.PYLTI_CONFIG


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    TESTING = True
    PYLTI_CONFIG = settings.PYLTI_CONFIG
    MONGO_URI = 'mongodb://localhost:27017/test_database'


class TestingConfig(BaseConfig):
    DEBUG = False
    TESTING = True
    PYLTI_CONFIG = settings.PYLTI_CONFIG

# DEFINE ADDITIONAL CONFIGS AS NEEDED
