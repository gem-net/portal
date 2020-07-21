import os
import logging
import requests
import datetime as dt
from collections import OrderedDict, defaultdict

import numpy as np
import pandas as pd

from . import app, db, MEMBERS_DICT, name_dict, DATA_DIR


logger = logging.getLogger(__name__)

TOKEN = app.config['ASANA_TOKEN']
WORKSPACE_ID = app.config['ASANA_WORKSPACE_ID']
TEAM_ID = app.config['ASANA_TEAM_ID']
# DEMO_PROJ_ID = '970226393478089'
# DEMO_TASK_ID = '982320718273845'
ASANA_HOST = 'https://app.asana.com/api/1.0/'
COLORMAP = defaultdict(lambda: '#b7bfc6')
COLORMAP.update({
        'dark-pink': '#ea4e9d',
        'dark-orange': '#fd612c',
        'dark-brown': '#eec300',
        'light-teal': '#37c5ab',
        'light-blue': '#4186e0',
        'dark-purple': '#7a6ff0',
        'light-purple': '#aa62e3',
    })

# OBJECTS POPULATED IN THIS MODULE: asana_ids, projects
asana_ids = None
projects = None
tasks = None
links = None

nan = np.nan
nat = pd._libs.tslibs.nattype.NaT


# LOCAL FILES FOR STORING LOADED DATA
ids_local = os.path.join(DATA_DIR, 'asana_ids.feather')
projects_local = os.path.join(DATA_DIR, 'projects.feather')
tasks_local = os.path.join(DATA_DIR, 'tasks.feather')
links_local = os.path.join(DATA_DIR, 'links.feather')


# USER IDS

def _request_user_ids():
    """Get dataframe of user emails, gids, names."""
    params = {
        'workspace': WORKSPACE_ID,
        'opt_fields': 'email,name'
        }
    endpoint = 'teams/{}/users/'.format(TEAM_ID)
    url = 'https://app.asana.com/api/1.0/{}'.format(endpoint)
    r = requests.get(url, params=params, auth=(TOKEN, ''))
    user_ids = pd.DataFrame.from_records(r.json()['data'])[
        ['email', 'gid', 'name']]. \
        rename(columns={'gid': 'asana_id', 'name': 'asana_name'}). \
        sort_values('asana_name').reset_index(drop=True)

    # user_ids['use_name'] = user_ids[]
    # Check for unrecognized emails
    emails_without_names = {i for i in user_ids.email if i not in name_dict}
    if emails_without_names:
        logger.warning("Some asana emails lack names: %s",
                       ', '.join(emails_without_names))
    return user_ids


def load_asana_ids():
    global asana_ids
    asana_ids = pd.read_feather(ids_local)


def update_asana_ids():
    """Update info on all asana users: email, asana_id, asana_name."""
    global asana_ids
    asana_ids = _request_user_ids()  # warns if email not recognized

    # CHECK FOR UNRECOGNIZED ASANA EMAILS
    _asana_emails = set(asana_ids.email)
    _extra_emails = _asana_emails.difference(set(MEMBERS_DICT.values()))
    logger.info("Asana emails not in members list: %s", _extra_emails)

    # CHECK FOR ASANA EMAILS THAT DON'T HAVE NAMES
    _emails_without_names = {i for i in _asana_emails if i not in name_dict}
    if _emails_without_names:
        logger.warning("Some asana emails lack names: %s", ', '.join(_emails_without_names))
    else:
        logger.info("All asana ids are associated with names.")
    # asana_ids['task_list'] = asana_ids['asana_id'].map(user_task_list_dict)
    asana_ids.to_feather(ids_local)


def get_asana_id_for_user(user):
    """Get personal asana user id for user database object. Update user object.

    Returns:
        asana_id (str): user's asana ID.
    """
    if user.asana_id:
        return user.asana_id
    asana_matches = asana_ids[asana_ids.email.isin(user.known_emails)]
    if not len(asana_matches):
        logger.warning("No asana match for %s", user.display_name)
        return None
    else:
        if len(asana_matches) > 1:
            logger.warning("%d asana matches for %s, using first match.",
                           len(asana_matches), user.use_name)
        asana_match = asana_matches.iloc[0]
    asana_id = asana_match.asana_id
    user.asana_id = asana_id
    db.session.add(user)
    db.session.commit()
    # task_list = asana_match.task_list
    return asana_id  # , task_list


# PROJECTS

def _abbreviate_project_name(name):
    max_len = 4
    if len(name) <= max_len:
        return name
    # first letters per word
    return ''.join([i[0] for i in name.split(' ')])


def _request_projects():
    """Get project metadata for all unarchived projects."""
    opt_fields = ['name', 'color', 'modified_at',
                  'followers', 'members', 'notes', 'owner', 'public',
                  'team', 'workspace']
    params = {
        'opt_fields': ','.join(opt_fields),
        'limit': 100,
        'archived': False
    }
    endpoint = 'teams/{}/projects'.format(TEAM_ID)
    url = 'https://app.asana.com/api/1.0/{}'.format(endpoint)
    logger.info("Looking up all projects for team.")
    r = requests.get(url, params=params, auth=(TOKEN, ''))
    data = r.json()['data']
    proj = pd.DataFrame.from_records(data, columns=opt_fields + ['gid'])
    proj.set_index('gid', inplace=True)
    proj.index.name = 'project_id'
    # SIMPLIFY DICTIONARY COLUMNS BY REDUCING TO (COMMA-SEPARATED) IDS
    for list_col in ['members', 'followers']:
        proj[list_col] = proj[list_col].apply(
            lambda f: ','.join([i['gid'] for i in f]))  # comma-separated IDs
    for dict_col in ['team', 'workspace', 'owner']:
        proj[dict_col] = [i['gid'] for i in proj[dict_col]]
    proj['hex_color'] = proj['color'].map(COLORMAP)
    proj['abbrev'] = proj['name'].map(_abbreviate_project_name)
    return proj


def load_projects():
    global projects
    temp = pd.read_feather(projects_local)
    temp.set_index('project_id', inplace=True)
    projects = temp


def update_projects_listing():
    global projects
    projects = _request_projects()
    temp = projects.reset_index()
    temp.to_feather(projects_local)


# TASKS

def _request_project_tasks(project_id):
    """Get incomplete tasks for project."""
    keep_cols = ['name', 'due_on', 'modified_at', 'html_notes', 'assignee']
    extra_cols = ['projects', 'memberships.(section|project).name']

    opt_fields = keep_cols + extra_cols

    params = {
        'opt_fields': ','.join(opt_fields),
        'completed_since': 'now'
    }
    endpoint = 'projects/{}/tasks'.format(project_id)
    url = 'https://app.asana.com/api/1.0/{}'.format(endpoint)
    r = requests.get(url, params=params, auth=(TOKEN, ''))
    data = r.json()['data']
    # item = pd.Series(r.json()['data'][0])
    # GET TASKS TABLE
    use_cols = keep_cols + ['gid']
    tasks = pd.DataFrame(data, columns=use_cols)
    # tasks['projects'] = [[i['gid'] for i in j] for j in tasks.projects]

    tasks.set_index('gid', inplace=True)
    tasks.index.name = 'task_id'
    tasks['html_notes'] = tasks.html_notes.apply(_remove_body_tags)
    tasks['assignee'] = [i['gid'] if type(i) == dict else i
                         for i in tasks['assignee'].values]
    tasks['due_ts'] = tasks['due_on'].apply(
        lambda v: pd.to_datetime(v, infer_datetime_format=True) if v else nat)
    tasks['due_this_year'] = tasks['due_ts'].apply(
        lambda v: v.date().year == dt.datetime.now().year)
    tasks['overdue'] = tasks.due_ts.apply(lambda v: v.date() < dt.date.today())
    tasks['url'] = ["https://app.asana.com/0/{workspace}/{task}"
                    .format(task=v, workspace=app.config['ASANA_WORKSPACE_ID'])
                    for v in tasks.index.values]

    m_list = []
    for task in data:
        # parse memberships
        memberships = task['memberships']
        for m_dict in memberships:
            proj = m_dict['project']
            sec = m_dict['section']
            m_dict = OrderedDict(task_id=task['gid'],
                                 project_id=proj['gid'],
                                 project_name=proj['name'],
                                 section_id=sec['gid'] if sec else None,
                                 section_name=sec['name'] if sec else None)
            m_list.append(m_dict)
    task_parents = pd.DataFrame.from_records(m_list)

    # # GET TASK-PROJECT MAP TABLE
    # map_tuples = []
    # for gid, projs in tasks['projects'].iteritems():
    #     for proj in projs:
    #         map_tuples.append((gid, proj))
    # task_projects = pd.DataFrame(data=map_tuples, columns=['task_id', 'project_id'])

    return tasks, task_parents


def load_tasks_links():
    global tasks, links
    tasks = pd.read_feather(tasks_local)
    links = pd.read_feather(links_local)


def update_tasks_links():
    """Gather tasks for all projects, and linkage between task, section, project."""
    global tasks, links

    all_tasks, all_parents = [], []
    project_ids = set(projects.index)
    for project_id in project_ids:
        tasks, parents = _request_project_tasks(project_id)
        all_tasks.append(tasks)
        all_parents.append(parents)
    links = pd.concat(all_parents, axis=0, ignore_index=True).drop_duplicates()

    # HANDLE UNRECOGNIZED PROJECT REFERENCES
    unknown_projects = set(links.project_id).difference(project_ids)
    if unknown_projects:
        # try lookup, drop if fails
        update_projects_listing()
        refreshed_proj_ids = set(projects.index)
        still_unknown = set(links.project_id).difference(refreshed_proj_ids)
        new_project_ids = refreshed_proj_ids.difference(project_ids)
        if new_project_ids:
            logger.info("Found new projects in links: %s", new_project_ids)
            for project_id in new_project_ids:
                tasks, parents = _request_project_tasks(project_id)
                all_tasks.append(tasks)
                all_parents.append(parents)
        if still_unknown:
            logger.info("Dropping unknown projects from links: %s",
                        still_unknown)
            links = links[~links.project_id.isin(still_unknown)] \
                .reset_index(drop=True)

    # Concatenate tasks and metadata, dropping duplicates (from redundant loading)
    tasks = pd.concat(all_tasks, axis=0, ignore_index=False).drop_duplicates()
    tasks = tasks.sort_values('due_on')
    tasks.reset_index(inplace=True)

    links = pd.concat(all_parents, axis=0, ignore_index=True).drop_duplicates()
    links['section_id'] = links['section_id'].fillna('0')  # use '0' for blanks
    links['section_name'] = links['section_name'].fillna('')
    links.reset_index(drop=True, inplace=True)

    tasks.to_feather(tasks_local)
    links.to_feather(links_local)


def get_task_dict_for_user(asana_id: str, include_unassigned=True):
    if include_unassigned:
        show_bool = (tasks.assignee.isnull()) | (tasks.assignee == asana_id)
    else:
        show_bool = tasks.assignee == asana_id
    show_tasks = tasks[show_bool].copy()
    show_tasks['mine'] = (show_tasks.assignee == asana_id)
    show_links = links[links.task_id.isin(show_tasks.task_id)]
    # show_proj_ids = show_links.project_id.unique()
    show_dict = defaultdict(OrderedDict)

    # warning: could be an issue if section names are repeated within a project
    for _, temp_tasks in show_links.groupby(['project_id', 'section_id']):
        project_name = temp_tasks.project_name.iloc[0]
        section_name = temp_tasks.section_name.iloc[0]
        sec_tasks = show_tasks[show_tasks.task_id.isin(temp_tasks.task_id)]
        show_dict[project_name][section_name] = sec_tasks
    #     print('{}: {}'.format(project_name, section_name))
    #     for i in sec_tasks['name']:
    #         print('\t{}'.format(i))
    return show_dict


def _remove_body_tags(html):
    front = '<body>'
    back = '</body>'
    if html.startswith(front):
        html = html[len(front):]
        if not html.endswith(back):
            raise Exception('Missing closing body tag in html: {}'.format(html))
        html = html[:-len(back)]
    return html


def load_user_assigned_tasks(user):
    """Get table of upcoming tasks assigned to db user.

    Returns:
        pd.DataFrame of tasks (including 'location' column) if asana match and
            if any tasks assigned to user, else None.
    """
    asana_id = get_asana_id_for_user(user)
    if asana_id is None:
        return

    my_tasks = tasks[tasks.assignee == asana_id].copy()
    if not len(my_tasks):
        return
    my_links = links[links.task_id.isin(my_tasks.task_id)]
    where_dict = {}
    for task_id, group in my_links.groupby('task_id'):
        where_dict[task_id] = [tuple(i) for i in
                               group[['project_name', 'section_name']].values]
    my_tasks['location'] = my_tasks.task_id.map(where_dict)
    return my_tasks



# GLOBALS: PROJECTS
load_asana_ids()  # update asana_ids
load_projects()  # update projects
load_tasks_links()  # update tasks, links


class Unused:

    @staticmethod
    def custom_request(endpoint, param_dict):
        """Test custom endpoint.

        Args:
            endpoint (str): e.g. 'teams/{}/users/'.format(TEAM_ID)
            param_dict (dict): e.g. params = {'workspace': WORKSPACE_ID,
                'opt_fields': 'email,name'}
        Returns:
            r: http response object.
        """
        # params = {
        #     'workspace': WORKSPACE_ID,
        #     'opt_fields': 'email,name'
        #     }
        # endpoint = 'teams/{}/users/'.format(TEAM_ID)
        url = 'https://app.asana.com/api/1.0/{}'.format(endpoint)
        r = requests.get(url, params=param_dict, auth=(TOKEN, ''))
        return r

    @staticmethod
    def unpack_records(df, col):
        """Convert column with list of dicts values to new dataframe, preserving index."""
        out = []
        ind_name = df.index.name
        for ind, r in df.iterrows():
            try:
                temp = pd.DataFrame.from_records(r[col])
            except ValueError:
                temp = pd.DataFrame(r[col], index=[ind])

            temp.insert(0, ind_name, ind)

            out.append(temp)
        out = pd.concat(out, axis=0)
        out.reset_index(drop=True, inplace=True)
        return out

    @staticmethod
    def add_first_last(names_df):
        """Add first and last name to dataframe, based on full_name column."""
        names_df['firstname'], names_df['lastname'] = \
            zip(*names_df['full_name'].apply(lambda v: v.split(' ')).values)
        return names_df.sort_values('lastname')

    @staticmethod
    def get_first_last_names(full_name):
        if type(full_name) == str:
            vals = full_name.split(' ')
            return vals[0], vals[1]
        else:
            return np.nan, np.nan

    @staticmethod
    def get_asana_user_task_lists():
        """Get dictionary of user_id: task_list_id for all users."""
        params = {
            'workspace': WORKSPACE_ID,
        }
        # name_ids = [tuple(i) for i in asana_ids[['asana_name', 'asana_id']].values]
        user_list_dict = {}
        user_ids = asana_ids['asana_id']
        logger.info('Fetching task list ids for %s users.', len(user_ids))
        for user_id in user_ids:  # for person_name, user_id in name_ids:
            # logger.info('Fetching list for %s', person_name)
            endpoint = 'users/{}/user_task_list'.format(user_id)
            url = 'https://app.asana.com/api/1.0/{}'.format(endpoint)
            r = requests.get(url, params=params, auth=(TOKEN, ''))
            """EXAMPLE RESPONSE
            {'data': {'id': 801620836635449,
             'gid': '801620836635449',
             'resource_type': 'user_task_list',
             'name': 'My Tasks',
             'owner': {'id': 801620836635456,
              'gid': '801620836635456',
              'name': 'joe.bloggs',
              'resource_type': 'user'},
             'workspace': {'id': 123456789876543,
              'gid': '123456789876543',
              'name': 'mydomain.net',
              'resource_type': 'workspace'}}}"""
            user_list_id = r.json()['data']['gid']
            user_list_dict[user_id] = user_list_id
        return user_list_dict

    @staticmethod
    def get_user_tasks(user):
        """NOT USED. Get task details and associated projects for user.

        Args:
            user: user object.

        Returns:
            tasks (pd.DataFrame): table of tasks.
            task_projects (pd.DataFrame): task_id, project_id table.
        """
        # NOTES: can use either notes or html_notes
        #     not in response if requested: ('owner', 'current_status', 'team')
        #     don't need: ('workspace', 'due_at')
        opt_fields = ['name', 'due_on', 'modified_at', 'projects', 'html_notes',
                      'memberships.(section|project).name']

        params = {
            'opt_fields': ','.join(opt_fields),
            'completed_since': 'now'
        }
        endpoint = 'user_task_lists/{}/tasks'.format(user.task_list_id)
        url = 'https://app.asana.com/api/1.0/{}'.format(endpoint)
        r = requests.get(url, params=params, auth=(TOKEN, ''))
        data = r.json()['data']
        # item = pd.Series(r.json()['data'][0])
        # GET TASKS TABLE
        use_cols = opt_fields + ['gid']
        tasks = pd.DataFrame(data, columns=use_cols)
        # tasks['projects'] = [[i['gid'] for i in j] for j in tasks.projects]
        tasks['html_notes'] = tasks.html_notes.apply(_remove_body_tags)
        tasks.set_index('gid', inplace=True)
        tasks.index.name = 'task_id'

        m_list = []
        for task in data:
            # parse memberships
            memberships = task['memberships']
            for m_dict in memberships:
                proj = m_dict['project']
                sec = m_dict['section']
                m_dict = OrderedDict(task_id=task['gid'],
                                     project_id=proj['gid'],
                                     project_name=proj['name'],
                                     section_id=sec['gid'] if sec else None,
                                     section_name=sec['name'] if sec else None)
                m_list.append(m_dict)
        task_parents = pd.DataFrame.from_records(m_list)

        # # GET TASK-PROJECT MAP TABLE
        # map_tuples = []
        # for gid, projs in tasks['projects'].iteritems():
        #     for proj in projs:
        #         map_tuples.append((gid, proj))
        # task_projects = pd.DataFrame(data=map_tuples, columns=['task_id', 'project_id'])

        return tasks, task_parents
