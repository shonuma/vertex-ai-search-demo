import json
import os

import google
import google.auth.transport.requests
import google.oauth2.credentials
import requests
from google.auth import compute_engine
from google.oauth2 import service_account

token = None

def retreive_token():
    global token

    # credentials, project_id = google.auth.default()
    credentials = service_account.Credentials.from_service_account_info(
        json.loads(os.environ['SERVICE_ACCOUNT_INFO']),
        scopes=[
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/cloud-platform',
            'openid',
            'email'
        ],
        subject=os.environ['SUBJECT'],
    )
    request = google.auth.transport.requests.Request()
    credentials.refresh(request)
    token = credentials.token
    return credentials.token


def get_token():
    global token
    return token
