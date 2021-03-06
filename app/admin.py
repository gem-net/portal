import logging
from collections import OrderedDict, namedtuple
from datetime import date, datetime, timezone, timedelta

import numpy as np
import pandas as pd
from flask import current_app
from google.oauth2 import service_account
from googleapiclient.discovery import build

from .helpers import parse_timestamp_str
from .drive import file_tree_to_df
from .models import User


logger = logging.getLogger(__name__)


def get_service_handles():
    """Get dictionary of {service_name: service_handle}."""
    SERVICE_ACCOUNT_FILE = current_app.config['SERVICE_ACCOUNT_FILE']
    # GROUP_KEY = current_app.config['GROUP_KEY']
    SCOPES = current_app.config['SCOPES']

    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    delegated_credentials = credentials.with_subject(
        current_app.config['CREDENTIALS_AS_USER'])

    dir_service = build('admin', 'directory_v1', credentials=delegated_credentials, cache_discovery=False)
    files_service = build('drive', 'v3', credentials=delegated_credentials, cache_discovery=False)
    cal_service = build('calendar', 'v3', credentials=delegated_credentials, cache_discovery=False)
    return {
        'dir': dir_service,
        'files': files_service,
        'cal': cal_service
    }


SERVICE_HANDLES = get_service_handles()


def get_members_dict():
    """Get dictionary of {google_id: email_address}.

    Return:
         members_dict (dict): google ID: email dictionary.
    """
    service = SERVICE_HANDLES['dir']

    # GOOGLE GROUP MEMBERS
    group_key = current_app.config['GROUP_KEY']
    logging.info("Looking up group members list.")
    res = service.members().list(groupKey=group_key).execute()
    members_dict = {i['id']: i['email'] for i in res['members'] if 'email' in i}

    # DOMAIN-ONLY MEMBERS
    domain_users = get_domain_users()
    domain_dict = {u.id: u.email for u in domain_users}
    members_dict.update(domain_dict)

    return members_dict


def get_domain_users():
    """Get list of domain users (who might not be in specified Google Group).

    Warning: will only fetch up to 100 users.
    """
    users = []
    service = SERVICE_HANDLES['dir']
    logger.info("Looking up domain-specific users.")
    res = service.users().list(customer='my_customer').execute()
    User = namedtuple('User', ['id', 'email', 'full_name'])
    for user in res['users']:
        user_id = user['id']
        full_name = user['name']['fullName']
        email = user['primaryEmail']
        users.append(User(user_id, email, full_name))
    return users


def find_user_by_email(find_email):
    user = None
    for u in User.query.all():
        if find_email in u.known_emails:
            user = u
            break
    return user


class ApiTable:
    cols_show = None  # subclasses will override
    cols_other = None

    def __init__(self):
        self._df = None  # subclasses will override
        self.last_refresh = datetime.utcnow()
        self.refresh_minutes = 1
        self.refresh_df()

    def refresh_df(self):
        """Subclasses will override this method."""
        pass

    @property
    def cols(self):
        return list(self.cols_show) + list(self.cols_other)

    @property
    def df(self):
        if datetime.utcnow() > (self.last_refresh + timedelta(minutes=self.refresh_minutes)):
            self.refresh_df()
            self.last_refresh = datetime.utcnow()
        return self._df

    @staticmethod
    def _get_utc_naive(dt):
        """Convert timezone aware timestamp to UTC naive timestamp."""
        return dt.astimezone(timezone.utc).replace(tzinfo=None)


class StatusTable(ApiTable):

    cols_show = OrderedDict([
        ('status', 'Status'),
        ('n_requests', 'Requests'),
        ])
    cols_other = []

    def __init__(self, engine):
        self.engine = engine
        super().__init__()

    def refresh_df(self):
        """Return status table. Example below.
                   status  n_requests
            0  Unassigned           2
            1  Processing           0
            2     Shipped           0
            3    Received           1
            4     Problem           0
            5   Cancelled           0
        """

        status_dict = OrderedDict([
            ('unassigned', 'Unassigned'),
            ('processing', 'Processing'),
            ('shipped', 'Shipped'),
            ('received', 'Received'),
            ('problem', 'Problem'),
            ('cancelled', 'Cancelled')])

        statuses = pd.read_sql("select status, count(*) as n_requests from strains.requests group by status;",
                               self.engine)
        statuses.status = statuses.status.apply(lambda v: status_dict[v])
        statuses = statuses.set_index('status').reindex(status_dict.values())
        statuses = statuses['n_requests'].apply(lambda v: 0 if np.isnan(v) else int(v)).reset_index()
        self._df = statuses


class Calendar(ApiTable):
    cols_show = OrderedDict([
        ('title', 'Item'),
        ('start', 'When'),
        ('location', 'Where')])
    cols_other = ['description', 'url', 'end']
    show_n = 5

    def refresh_df(self):
        service = SERVICE_HANDLES['cal']
        collection = service.events()
        cmd = collection.list(calendarId=current_app.config['CALENDAR_ID'],
                              orderBy='startTime',
                              singleEvents=True)
        res = cmd.execute()

        cal = pd.DataFrame.from_records(res['items'])
        cal.rename(columns={'htmlLink': 'url', 'summary': 'title'}, inplace=True)
        cal = cal[self.cols].copy()
        cal['location'] = cal['location'].apply(lambda v: '' if type(v) != str else v)
        cal['start'] = cal['start'].apply(Calendar.parse_datetime)
        cal['end'] = cal['end'].apply(Calendar.parse_datetime)
        cal['in_past'] = cal['end'].apply(Calendar.in_past)
        cal['description'] = cal['description'].apply(
            lambda v: v.strip() if type(v) is str else '')
        cal = cal.query('~in_past').head(self.show_n)
        self._df = cal

    @staticmethod
    def parse_datetime(start_dict):
        """Get naive datetime in UTC or date for dates."""
        if 'dateTime' in start_dict:
            return parse_timestamp_str(start_dict['dateTime'])
        if 'date' in start_dict:
            return datetime.strptime(start_dict['date'], '%Y-%m-%d').date()

    @staticmethod
    def parse_time(time):
        """Return naive datetime in UTC."""
        if pd.isnull(time):
            return np.nan
        stripped = time[:-3] + time[-2:]  # remove colon in UTC offset
        dt = datetime.strptime(stripped, '%Y-%m-%dT%H:%M:%S%z')
        return ApiTable._get_utc_naive(dt)

    @staticmethod
    def in_past(t):
        """Get 'in past' status (True or False) for date or time.

        Args:
            t: timezone aware or naive timestamps, or date
        """
        now_naive = datetime.now()
        now = now_naive if t.tzinfo is None else now_naive.replace(tzinfo=timezone.utc)
        if isinstance(t, datetime):
            return t < now
        if type(t) == date:
            end_time = datetime.combine(t, datetime.min.time()) + timedelta(days=1)
            end_time = end_time.replace(tzinfo=timezone.utc)
            return end_time < now


class RecentDocs(ApiTable):
    cols_show = OrderedDict([
        ('title', 'Document'),
        ('date_modified', 'Modified'),
        ('last_user', 'Modified by')])

    cols_other = ['date_created', 'url', 'icon', 'kind', 'thumb']
    show_n = 20

    def refresh_df(self):
        service = SERVICE_HANDLES['files']
        file_fields = ("files(kind,id,name,webViewLink,iconLink,thumbnailLink,createdTime,"
                       "modifiedTime,lastModifyingUser/displayName)")
        collection = service.files()
        cmd = collection.list(corpora='teamDrive',
                              includeTeamDriveItems=True,
                              orderBy='modifiedTime desc',
                              pageSize=20,
                              supportsTeamDrives=True,
                              teamDriveId=current_app.config['TEAM_DRIVE_ID'],
                              fields=file_fields)
        res = cmd.execute()
        files = pd.DataFrame.from_records(res['files'])
        files.lastModifyingUser = files.lastModifyingUser.apply(
            lambda v: v['displayName'] if type(v) == dict else v)
        files.createdTime = files.createdTime.apply(parse_timestamp_str)
        files.modifiedTime = files.modifiedTime.apply(parse_timestamp_str)
        files.rename(columns={'webViewLink': 'url',
                              'thumbnailLink': 'thumb',
                              'iconLink': 'icon',
                              'modifiedTime': 'date_modified',
                              'createdTime': 'date_created',
                              'lastModifyingUser': 'last_user',
                              'name': 'title'
                              }, inplace=True)
        # not used: 'id'
        # file_columns = ['title', 'date_modified', 'date_created', 'last_user', 'url', 'icon' , 'kind', 'thumb']
        files = files[self.cols].copy()
        self._df = files


class ReviewTable(ApiTable):

    def __init__(self, root_folder_id, root_folder_title):
        self.refresh_minutes = 5
        self.root_folder_id = root_folder_id
        self.root_folder_title = root_folder_title
        super().__init__()

    cols_show = OrderedDict([
        ('title', 'Document'),
        ('date_modified', 'Modified'),
        # ('last_user', 'Modified by')
    ])
    cols_other = ['path', 'date_created', 'icon', 'id', 'kind', 'last_user', 'mimeType',
                  'thumb', 'url_content', 'url_view']
    # cols_other = ['date_created', 'url', 'icon', 'kind', 'thumb']

    def refresh_df(self):
        files = file_tree_to_df(self.root_folder_id, self.root_folder_title)
        files = files[list(ReviewTable.cols_show) + ReviewTable.cols_other]
        files = files.sort_values(['path', 'title'])
        self._df = files
