import os
import sys
from datetime import datetime
import logging

from flask import Flask, g, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_bootstrap import Bootstrap
from flask_mail import Mail
from flask_moment import Moment
import pandas as pd

from .oauth import OAuthSignIn
from .config import config


logging.basicConfig(level=logging.INFO, stream=sys.stdout)

app = Flask(__name__)
app.config.from_object(config[os.getenv('FLASK_ENV') or 'default'])

db = SQLAlchemy(app)

bootstrap = Bootstrap()
bootstrap.init_app(app)

lm = LoginManager(app)
lm.login_view = 'index'

mail = Mail()
mail.init_app(app)

moment = Moment(app)

MEMBERS_DICT = {}
TABLE_DICT = {}

basedir = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(basedir, 'data')


@app.before_request
def before_request():
    update_g()
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        # first-request data reload might be necessary for auto-restart development
        current_user.in_cgem = current_user.social_id in g.members_dict
        db.session.commit()


def update_g():
    g.members_dict = MEMBERS_DICT
    g.cal = TABLE_DICT['cal']
    g.recent_docs = TABLE_DICT['recent_docs']
    g.statuses = TABLE_DICT['statuses']
    # g.review = TABLE_DICT['review']


def update_members_dict():
    """Update members dictionary"""
    global MEMBERS_DICT
    MEMBERS_DICT.clear()
    with app.app_context():
        from .admin import get_members_dict
        new_dict = get_members_dict()
    MEMBERS_DICT.update(new_dict)


def update_table_dict():
    global TABLE_DICT
    with app.app_context():
        from .admin import Calendar, RecentDocs, StatusTable, ReviewTable
        TABLE_DICT.clear()
        TABLE_DICT.update({
            'cal': Calendar(),
            'recent_docs': RecentDocs(),
            'statuses': StatusTable(db.engine),
        })


def _load_name_dict():
    """Load email: name dictionary from local file."""
    email_names = pd.read_table(os.path.join(DATA_DIR, 'email_names.tsv'), sep='\t',
                                header=None, names=['email', 'full_name'])
    name_dict = email_names.set_index('email')['full_name'].to_dict()
    return name_dict


def update_name_dict():
    global name_dict
    name_dict.clear()
    new_dict = _load_name_dict()
    name_dict.update(new_dict)


name_dict = _load_name_dict()
update_members_dict()
update_table_dict()

from app import models
from app import routes
