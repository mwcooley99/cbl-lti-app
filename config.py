import settings
from configparser import ConfigParser


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


# def db_config(filename='database.ini', section='postgresql'):
#     # create a parser
#     parser = ConfigParser()
#     # read config file
#     parser.read(filename)
#
#     # get section, default to postgresql
#     db = {}
#     if parser.has_section(section):
#         params = parser.items(section)
#         for param in params:
#             db[param[0]] = param[1]
#     else:
#         raise Exception(
#             'Section {0} not found in the {1} file'.format(section, filename))
#
#     return db