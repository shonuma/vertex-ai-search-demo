import json

import google
import google.auth.transport.requests
import google.oauth2.credentials
import requests
from google.auth import compute_engine

token = None

def retreive_token():
    global token

    url = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
    header = {
        "Metadata-Flavor": "Google"
    }
    response = requests.get(url, headers=header)
    token = json.loads(response.text).get('access_token')
    return token


def get_token():
    global token
    return token
