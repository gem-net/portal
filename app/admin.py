from collections import OrderedDict
from datetime import date, datetime, timezone, timedelta

import pandas as pd
from flask import current_app
from google.oauth2 import service_account
from googleapiclient.discovery import build
# from httplib2 import Http
# from oauth2client import file, client, tools


def get_service_handles():
    """Get dictionary of {service_name: service_handle}."""
    SERVICE_ACCOUNT_FILE = current_app.config['SERVICE_ACCOUNT_FILE']
    GROUP_KEY = current_app.config['GROUP_KEY']
    SCOPES = current_app.config['SCOPES'] 

    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    delegated_credentials = credentials.with_subject('stephen@gem-net.net')

    dir_service = build('admin', 'directory_v1', credentials=delegated_credentials)
    files_service = build('drive', 'v3', credentials=delegated_credentials)
    cal_service = build('calendar', 'v3', credentials=delegated_credentials)
    return {
        'dir': dir_service,
        'files': files_service,
        'cal': cal_service
    }


SERVICE_HANDLES = get_service_handles()


def get_members_dict():
    """Get dictionary of {google_id: email_address}."""    
    service = SERVICE_HANDLES['dir']
    group_key = current_app.config['GROUP_KEY']
    res = service.members().list(groupKey=group_key).execute()
    members_dict = dict([(i['id'], i['email']) for i in res['members'] if 'email' in i])
    return members_dict


class ApiTable():
    
    def __init__(self):
        self.last_refresh = datetime.utcnow()
        self.refresh_df()

    @property
    def cols(self):
        return list(self.cols_show) + list(self.cols_other)

    @property
    def df(self):
        if datetime.utcnow() > (self.last_refresh + timedelta(minutes=1)):
            self.refresh_df()
            self.last_refresh = datetime.utcnow()
        return self._df


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

        statuses = pd.read_sql("select status, count(*) as n_requests from strains.requests group by status;", self.engine)
        statuses.status = statuses.status.apply(lambda v: status_dict[v])
        statuses = statuses.set_index('status').reindex(status_dict.values())
        statuses = statuses['n_requests'].apply(lambda v: 0 if pd.np.isnan(v) else int(v)).reset_index()
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
        cmd = collection.list(calendarId='gem-net.net_93bpcnm07c6l0d56eqgssq3eik@group.calendar.google.com',
                      orderBy='startTime',
                      singleEvents=True)
        res = cmd.execute()
        
        cal = pd.DataFrame.from_records(res['items'])
        cal.rename(columns={'htmlLink': 'url', 'summary': 'title'}, inplace=True)
        cal = cal[self.cols].copy()
        cal['start'] = cal['start'].apply(Calendar.parse_datetime)
        cal['end'] = cal['end'].apply(Calendar.parse_datetime)
        cal['in_past'] = cal['end'].apply(Calendar.in_past)

        cal = cal.query('~in_past').head(self.show_n)
        self._df = cal

    @staticmethod
    def parse_datetime(start_dict):
        if 'dateTime' in start_dict:
            return Calendar.parse_time(start_dict['dateTime'])
        if 'date' in start_dict:
            return datetime.strptime(start_dict['date'], '%Y-%m-%d').date()

    @staticmethod
    def parse_time(time):
        if pd.isnull(time):
            return pd.np.nan
        stripped = time[:-3] + time[-2:]  # remove colon in UTC offset
        return datetime.strptime(stripped, '%Y-%m-%dT%H:%M:%S%z')
     
    @staticmethod
    def in_past(t):
        now = datetime.now(timezone.utc)
        if type(t) == datetime:
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

    cols_other = ['date_created', 'url', 'icon' , 'kind', 'thumb']
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
        files.lastModifyingUser = files.lastModifyingUser.apply(lambda v: v['displayName'])
        files.createdTime = files.createdTime.apply(RecentDocs.parse_timestamp_str)
        files.modifiedTime = files.modifiedTime.apply(RecentDocs.parse_timestamp_str)
        files.rename(columns={'webViewLink': 'url',
                              'thumbnailLink': 'thumb',
                              'iconLink': 'icon',
                              'modifiedTime': 'date_modified',
                              'createdTime': 'date_created',
                              'lastModifyingUser': 'last_user',
                              'name': 'title'
                             }, inplace=True)
        # not used: 'id'
        #file_columns = ['title', 'date_modified', 'date_created', 'last_user', 'url', 'icon' , 'kind', 'thumb']
        files = files[self.cols].copy()
        self._df = files

    @staticmethod
    def parse_timestamp_str(time):
        # manual version
        # datetime.strptime(time, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
        timestamp = pd.to_datetime(time).replace(tzinfo=timezone.utc)
        # dt = timestamp.to_pydatetime().replace(tzinfo=timezone.utc)
        return timestamp
