#!/usr/bin/env python3
"""
Google認証の再実行スクリプト
全てのGoogle Workspace APIサービスに対して再認証を行います。
"""

import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import pickle

# 必要なスコープを全て定義
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'openid'
]

def main():
    """全サービスに対して再認証を実行"""
    creds = None
    token_file = 'token.json'
    credentials_file = 'credentials.json'

    # 既存のトークンファイルをバックアップ
    if os.path.exists(token_file):
        backup_file = f'{token_file}.backup'
        os.rename(token_file, backup_file)
        print(f'✅ Backed up existing token to {backup_file}')

    # credentials.jsonの存在確認
    if not os.path.exists(credentials_file):
        print(f'❌ {credentials_file} not found!')
        print('Please download OAuth 2.0 credentials from Google Cloud Console')
        return

    # OAuth フローを実行
    print('🔐 Starting OAuth flow...')
    print('📋 Required scopes:')
    for scope in SCOPES:
        print(f'  - {scope}')

    flow = InstalledAppFlow.from_client_secrets_file(
        credentials_file,
        SCOPES
    )

    # ローカルサーバーを起動して認証
    creds = flow.run_local_server(port=0)

    # トークンを保存
    with open(token_file, 'w') as token:
        token.write(creds.to_json())

    print(f'✅ Successfully authenticated!')
    print(f'✅ Token saved to {token_file}')

    # 認証されたアカウント情報を表示
    from googleapiclient.discovery import build
    service = build('drive', 'v3', credentials=creds)
    about = service.about().get(fields='user').execute()
    user = about.get('user', {})

    print('\n👤 Authenticated as:')
    print(f'   Email: {user.get("emailAddress")}')
    print(f'   Display Name: {user.get("displayName")}')

if __name__ == '__main__':
    main()
