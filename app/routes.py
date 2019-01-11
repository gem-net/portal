from datetime import datetime

from flask import redirect, url_for, render_template, flash, abort, g, send_file
from flask_login import login_user, logout_user,\
    current_user

from app import app, db, OAuthSignIn, update_members_and_tables
from .models import User


@app.route('/reload')
def load_members_list():
    if current_user.is_authenticated and current_user.in_cgem:
        update_members_and_tables()
        n_members = len(g.members_dict)
        msg = 'Emails and members list updated ({} members).'.format(n_members)
        flash(msg, 'message')
        return render_template('reload.html')
    else:
        abort(404)


@app.route('/',  methods=['POST', 'GET'])
def index():
    if not (current_user.is_authenticated and current_user.in_cgem):
        return render_template("index.html")
    return render_template("index.html", cal=g.cal, docs=g.recent_docs, statuses=g.statuses)


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
    if not current_user.is_anonymous:
        return redirect(url_for('index'))
    oauth_obj = OAuthSignIn.get_provider(provider)
    social_id, username, email = oauth_obj.callback()
    if social_id is None:
        flash('Authentication failed.', 'error')
        return redirect(url_for('index'))
    user = User.query.filter_by(social_id=social_id).first()
    if not user:
        if social_id in g.members_dict:
            email = g.members_dict[social_id]
        user = User(social_id=social_id, display_name=username, email=email)
        db.session.add(user)
        db.session.commit()
    login_user(user, True)
    return redirect(url_for('index'))


@app.route('/review')
def review():
    if not (current_user.is_authenticated and current_user.in_cgem):
        return render_template("index.html")
    return render_template("review.html", df=g.review.df, cols_show=g.review.cols_show)


@app.route('/download/<file_id>')
def download(file_id):
    from .review import download_file

    files = g.review.df
    try:
        file_info = files[files.id == file_id].iloc[0]
    except IndexError:
        flash('File not found', 'error')
        return redirect(url_for('download'))
    title = file_info.title
    mime_orig = file_info.mimeType
    fh, filename, mime_out = download_file(file_id, title=title, mime_orig=mime_orig)
    fh.seek(0)
    return send_file(fh, mimetype=mime_out,
                     as_attachment=True, attachment_filename=filename)


@app.route('/build_zip')
def get_folder_zip():
    from .review import download_folder_zip

    files = g.review.df
    zipped_file = download_folder_zip(files)
    time_str = datetime.utcnow().strftime('%Y-%m-%d_%H:%M:%SZ')
    out_name = 'C-GEM_files_{}.zip'.format(time_str)
    zipped_file.seek(0)
    return send_file(zipped_file, mimetype='application/zip',
                     as_attachment=True, attachment_filename=out_name)
