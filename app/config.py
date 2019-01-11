import os
import logging

from dotenv import load_dotenv, find_dotenv

logger = logging.getLogger(__name__)

# basedir = os.path.abspath(os.path.dirname(__file__))
# env_path = os.path.join(basedir, '.env')
env_path = find_dotenv()
logger.info(env_path)
load_dotenv(env_path)


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
    APP_URL = os.environ.get('APP_URL')
    SERVER_NAME = os.environ.get('SERVER_NAME')

    OAUTH_CREDENTIALS = {
        'google': {
            'id': os.environ.get('GOOGLE_CLIENT_ID'),
            'secret': os.environ.get('GOOGLE_SECRET')
        }
    }
    DB_CNF = os.environ.get('DB_CNF')
    DB_HOST = os.environ.get('DB_HOST')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # recycle connection before mysql default 8hr wait timeout
    SQLALCHEMY_POOL_RECYCLE = int(
        os.environ.get('SQLALCHEMY_POOL_RECYCLE', 3600))

    SERVICE_ACCOUNT_FILE = os.environ.get('SERVICE_ACCOUNT_FILE')
    CREDS_JSON = os.environ.get('CREDS_JSON')
    GROUP_KEY = os.environ.get('GROUP_KEY')
    SCOPES = [
        'https://www.googleapis.com/auth/admin.directory.group.member.readonly',
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/drive.metadata.readonly',
        'https://www.googleapis.com/auth/calendar.readonly',
        'https://www.googleapis.com/auth/calendar.events.readonly']

    TEAM_DRIVE_ID = os.environ.get('TEAM_DRIVE_ID')

    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_SENDER = os.environ.get('MAIL_SENDER')

    REVIEW_FOLDER_ID = os.environ.get('REVIEW_FOLDER_ID')
    REVIEW_FOLDER_TITLE = os.environ.get('REVIEW_FOLDER_TITLE')


class DevelopmentConfig(Config):
    DEBUG = True
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL_DEV') or \
        'sqlite:///' + os.path.join(basedir, 'db.sqlite')
    DB_NAME = os.environ.get('DB_NAME_DEV')
    SQLALCHEMY_ECHO = os.environ.get('SQLALCHEMY_ECHO') == 'True'


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data.sqlite')
    DB_NAME = os.environ.get('DB_NAME')


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,

    'default': DevelopmentConfig
}
