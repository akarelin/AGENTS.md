#!/usr/bin/env python3
"""Google API client — OAuth2 user credentials for Gmail and Drive.

All secrets from Azure Key Vault via gppu:
  - google-oauth-client-id      OAuth2 client ID
  - google-oauth-client-secret  OAuth2 client secret
  - google-oauth-token          OAuth2 token JSON (refresh_token, etc.)
"""
from __future__ import annotations

import json
import os
import sys

from gppu import resolve_secret

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
]

# Key Vault secret names
KV_CLIENT_ID = "google-oauth-client-id"
KV_CLIENT_SECRET = "google-oauth-client-secret"
KV_TOKEN = "google-oauth-token"


def _get_client_config():
    """Build OAuth2 client config from Key Vault secrets."""
    return {
        "installed": {
            "client_id": resolve_secret(KV_CLIENT_ID),
            "client_secret": resolve_secret(KV_CLIENT_SECRET),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }


def _load_token_from_kv():
    """Try to load token JSON from Key Vault. Returns None if not found."""
    try:
        token_json = resolve_secret(KV_TOKEN)
        if token_json:
            data = json.loads(token_json)
            if data.get("refresh_token"):
                return token_json
    except Exception:
        pass
    return None


def _save_token_to_kv(token_json: str):
    """Save token JSON to Key Vault."""
    from gppu import set_secret
    set_secret(KV_TOKEN, token_json)


def save_token(token_json: str):
    """Save a token JSON string to Key Vault."""
    json.loads(token_json)  # validate before saving
    _save_token_to_kv(token_json)


def get_credentials():
    """Get or refresh OAuth2 credentials. Token stored in Key Vault."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    token_json = _load_token_from_kv()
    if token_json:
        creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            client_config = _get_client_config()
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)
        _save_token_to_kv(creds.to_json())

    return creds


def gmail_service():
    from googleapiclient.discovery import build
    return build("gmail", "v1", credentials=get_credentials())


def drive_service():
    from googleapiclient.discovery import build
    return build("drive", "v3", credentials=get_credentials())
