from collections import OrderedDict

from flask import redirect, url_for, render_template, flash, abort, \
    current_app, request, session
from flask_login import login_user, logout_user,\
    current_user, login_required

from app import app, db, OAuthSignIn, update_members_and_emails, MEMBERS_DICT
from .models import User


@app.route('/reload')
def load_members_list():
    if current_user.is_authenticated and current_user.in_cgem:
        update_members_and_emails()
        n_members = len(MEMBERS_DICT)
        msg = 'Emails and members list updated ({} members).'.format(n_members)
        flash(msg, 'message')
        return render_template('reload.html')
    else:
        abort(404)


@app.route('/',  methods=['POST', 'GET'])
def index():
    # if not (current_user.is_authenticated and current_user.in_cgem):
    return render_template("index.html")


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/authorize/<provider>')
def oauth_authorize(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('index'))
    oauth_obj = OAuthSignIn.get_provider(provider)
    return oauth_obj.authorize()


@app.route('/callback/<provider>')
def oauth_callback(provider):
    global MEMBERS_DICT
    if not current_user.is_anonymous:
        return redirect(url_for('index'))
    oauth_obj = OAuthSignIn.get_provider(provider)
    social_id, username, email = oauth_obj.callback()
    if social_id is None:
        flash('Authentication failed.', 'error')
        return redirect(url_for('index'))
    user = User.query.filter_by(social_id=social_id).first()
    if not user:
        if social_id in MEMBERS_DICT:
            email = MEMBERS_DICT[social_id]
        user = User(social_id=social_id, display_name=username, email=email)
        db.session.add(user)
        db.session.commit()
    login_user(user, True)
    return redirect(url_for('index'))
