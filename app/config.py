import os
import logging

from dotenv import load_dotenv, find_dotenv

logger = logging.getLogger(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
# env_path = os.path.join(basedir, '.env')
env_path = os.getenv('ENV_NAME', find_dotenv())
logger.info("Loading .env from %s", env_path)
load_dotenv(env_path, override=True)


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
    DB_HOST = os.environ.get('DB_HOST')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # recycle connection before mysql default 8hr wait timeout
    SQLALCHEMY_POOL_RECYCLE = int(
        os.environ.get('SQLALCHEMY_POOL_RECYCLE', 3600))

    SERVICE_ACCOUNT_FILE = os.environ.get('SERVICE_ACCOUNT_FILE')
    CREDENTIALS_AS_USER = os.environ.get('CREDENTIALS_AS_USER')
    CREDS_JSON = os.environ.get('CREDS_JSON')
    GROUP_KEY = os.environ.get('GROUP_KEY')
    SCOPES = [
        'https://www.googleapis.com/auth/admin.directory.user.readonly',
        'https://www.googleapis.com/auth/admin.directory.group.member.readonly',
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/drive.metadata.readonly',
        'https://www.googleapis.com/auth/calendar.readonly',
        'https://www.googleapis.com/auth/calendar.events.readonly']

    CALENDAR_ID = os.environ.get('CALENDAR_ID')
    TEAM_DRIVE_ID = os.environ.get('TEAM_DRIVE_ID')

    COMPOUNDS_DIR_ID = os.environ.get('COMPOUNDS_DIR_ID')
    COMPOUNDS_PICKLE = os.environ.get('COMPOUNDS_PICKLE')

    ASANA_TOKEN = os.environ.get('ASANA_TOKEN', None)
    ASANA_WORKSPACE_ID = os.environ.get('ASANA_WORKSPACE_ID', None)
    ASANA_TEAM_ID = os.environ.get('ASANA_TEAM_ID', None)


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
