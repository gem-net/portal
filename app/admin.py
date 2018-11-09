from collections import OrderedDict

import pandas as pd
from flask import current_app
from google.oauth2 import service_account
from googleapiclient.discovery import build


def get_members_dict():
    """Get dictionary of {google_id: email_address}."""
    SERVICE_ACCOUNT_FILE = current_app.config['SERVICE_ACCOUNT_FILE']
    GROUP_KEY = current_app.config['GROUP_KEY']
    SCOPES = current_app.config['SCOPES']

    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    delegated_credentials = credentials.with_subject('stephen@gem-net.net')

    # GET: https://www.googleapis.com/admin/directory/v1/groups/04i7ojhp13c8l10/members
    service = build('admin', 'directory_v1', credentials=delegated_credentials)
    res = service.members().list(groupKey=GROUP_KEY).execute()
    members_dict = dict([(i['id'], i['email']) for i in res['members'] if 'email' in i])
    return members_dict
