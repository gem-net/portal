import os
from datetime import datetime

from flask import Flask, g, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_bootstrap import Bootstrap
from flask_mail import Mail
from flask_moment import Moment

from .oauth import OAuthSignIn
from .config import config

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


@app.before_request
def before_request():
    update_g()
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        # first-request data reload might be necessary for auto-restart development
        current_user.in_cgem = current_user.social_id in g.members_dict
        # ADJUST EMAIL IF NECESSARY
        if current_user.in_cgem:
            current_user.email = g.members_dict[current_user.social_id]
        if current_user.email.endswith('@gem-net.net'):
            current_user.in_cgem = True
        db.session.commit()
    #     g.search_form = SearchForm()
    # g.locale = str(get_locale())


def update_g():
    g.members_dict = MEMBERS_DICT
    g.cal = TABLE_DICT['cal']
    g.recent_docs = TABLE_DICT['recent_docs']
    g.statuses = TABLE_DICT['statuses']
    g.review = TABLE_DICT['review']


@app.before_first_request
def update_members_and_tables():
    from .admin import get_members_dict, Calendar, RecentDocs, StatusTable, ReviewTable
    MEMBERS_DICT.clear()
    new_dict = get_members_dict()
    MEMBERS_DICT.update(new_dict)

    review_folder_id = current_app.config['REVIEW_FOLDER_ID']
    review_folder_title = current_app.config['REVIEW_FOLDER_TITLE']

    TABLE_DICT.clear()
    TABLE_DICT.update({
        'cal': Calendar(),
        'recent_docs': RecentDocs(),
        'statuses': StatusTable(db.engine),
        'review': ReviewTable(review_folder_id, review_folder_title),
    })


from app import models
from app import routes
