import logging

from flask import redirect, url_for, render_template, flash, abort, g, request
from flask_login import login_user, logout_user,\
    current_user

from app import app, db, OAuthSignIn, update_table_dict, update_members_dict, \
    update_name_dict
from .asana import update_asana_ids, update_projects_listing, \
    get_asana_id_for_user, load_user_assigned_tasks, \
    get_task_dict_for_user, projects, update_tasks_links
from .models import User
from .decorators import membership_required
from .admin import find_user_by_email


_logger = logging.getLogger(__name__)


@app.route('/reload')
@membership_required
def reload_all_data():
    update_table_dict()
    update_members_dict()
    update_name_dict()
    update_asana_ids()
    update_projects_listing()
    update_tasks_links()
    n_members = len(g.members_dict)
    msg = 'Members list and tasks updated ({} members).'.format(n_members)
    flash(msg, 'message')
    return render_template('reload.html')


@app.route('/update-tasks')
@membership_required
def update_tasks():
    update_projects_listing()
    update_tasks_links()
    msg = 'Task list updated.'
    flash(msg, 'message')
    return redirect(url_for('asana_tasks'))


@app.route('/',  methods=['POST', 'GET'])
def index():
    if not (current_user.is_authenticated and current_user.in_cgem):
        return render_template("index.html")
    email = request.args.get('email', '')
    user = find_user_by_email(email) if email else None
    user = user if user else current_user
    my_tasks = load_user_assigned_tasks(user)
    abbrv_colors = projects.set_index('name')[['abbrev', 'hex_color']]\
        .apply(lambda r: tuple(r), axis=1).to_dict()
    return render_template("index.html", cal=g.cal, docs=g.recent_docs,
                           statuses=g.statuses, my_tasks=my_tasks,
                           abbrv_colors=abbrv_colors)


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
    social_id, username, email, alt_email_str = oauth_obj.callback()
    if social_id is None:
        flash('Authentication failed.', 'error')
        return redirect(url_for('index'))
    user = User.query.filter_by(social_id=social_id).first()
    modified = False
    # CREATE NEW USER IF NOT IN DB
    if not user:
        if social_id in g.members_dict:
            email = g.members_dict[social_id]
        user = User(social_id=social_id, display_name=username, email=email,
                    alt_email_str=alt_email_str)
        modified = True
    use_name = user.get_official_name()
    # UPDATE EMAIL DATA IF NECESSARY
    if user.email != email or user.alt_email_str != alt_email_str \
            or user.use_name != use_name:
        user.email = email
        user.alt_email_str = alt_email_str
        user.use_name = use_name
        modified = True
    # GET ASANA IDS IF MATCH PRESENT
    if user.asana_id is None:
        asana_id = get_asana_id_for_user(user)
        if asana_id:
            user.asana_id = asana_id
            modified = True
    if modified:
        db.session.add(user)
        db.session.commit()
    login_user(user, True)
    return redirect(url_for('index'))


@app.route('/compounds',  methods=['GET'])
@membership_required
def show_compounds():
    from .compounds import get_categ_tables, SUMMARY_COL_DICT
    show_cols = list()
    for col in SUMMARY_COL_DICT:
        if SUMMARY_COL_DICT[col][1]:
            show_cols.append(col)
    categories, categ_tables = get_categ_tables()
    return render_template("compounds.html",
                           categories=categories,
                           categ_tables=categ_tables,
                           show_cols=show_cols,
                           col_dict=SUMMARY_COL_DICT)


@app.route('/compounds/<compound_safe>',  methods=['GET'])
@membership_required
def show_single_compound(compound_safe):
    from .compounds import COMPOUNDS, SINGLE_COL_DICT
    col_dict = SINGLE_COL_DICT
    overview_cols = list()
    single_cols = list()
    for col in col_dict:
        if col_dict[col][1] == 'overview':
            overview_cols.append(col)
        elif col_dict[col][1] == 'single':
            single_cols.append(col)
    c = COMPOUNDS['all'].loc[lambda v: v.compound_safe == compound_safe]
    c.sort_values(['is_doc', 'title'], ascending=[False, True], inplace=True)
    docs = c[c.is_doc]
    data = c[c.is_data]
    if not len(c):
        abort(404)
    return render_template("compound_single.html",
                           c=c, data=data, docs=docs,
                           overview_cols=overview_cols,
                           single_cols=single_cols,
                           col_dict=SINGLE_COL_DICT)


@app.route('/reload-compounds',  methods=['GET'])
@membership_required
def reload_compounds():
    from .compounds import reload_listing, load_prebuilt_listing
    reload_listing()
    flash("Compound re-indexing in progress, and may take up to 20 seconds.",
          'message')
    return redirect(url_for('index'))


@app.route('/asana',  methods=['GET'])
@membership_required
def asana_tasks():
    """Show all unassigned and user-assigned tasks."""
    color_dict = projects[['name', 'hex_color']]\
        .set_index('name')['hex_color'].to_dict()
    _logger.info("color_dict: %s", color_dict)
    email = request.args.get('email', '')
    user = find_user_by_email(email) if email else None
    user = user if user else current_user
    asana_id = get_asana_id_for_user(user)
    show_dict = get_task_dict_for_user(asana_id)
    return render_template("asana.html", show_dict=show_dict,
                           color_dict=color_dict)
