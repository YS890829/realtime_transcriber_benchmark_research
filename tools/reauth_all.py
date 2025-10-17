#!/usr/bin/env python3
"""
Google API Re-authentication with full scopes
Drive + Calendar scopes for complete functionality
"""
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import os

# Drive + Calendar スコープで再認証
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/calendar.readonly'
]

def main():
    print("=" * 60)
    print("Google API 再認証（Drive + Calendar）")
    print("=" * 60)
    print("スコープ:")
    for scope in SCOPES:
        print(f"  - {scope}")
    print()
    print("権限:")
    print("  - Google Drive: ファイルの読み取り・書き込み・削除")
    print("  - Google Calendar: 予定の読み取り")
    print()

    # 既存のtoken.jsonを削除
    if os.path.exists('token.json'):
        os.remove('token.json')
        print("✅ 古いtoken.jsonを削除しました")

    # 新しい認証フローを開始
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)

    print()
    print("ブラウザが自動的に開きます...")
    print("Google アカウントで認証してください。")
    print()

    # ローカルサーバーで認証（自動的にブラウザが開く）
    creds = flow.run_local_server(port=8080)

    # token.jsonに保存
    with open('token.json', 'w') as token:
        token.write(creds.to_json())

    print()
    print("=" * 60)
    print("✅ 再認証完了！")
    print("=" * 60)
    print("token.jsonが更新されました。")
    print("以下の権限が付与されました:")
    print("  ✅ Google Drive: ファイル操作")
    print("  ✅ Google Calendar: 予定読み取り")
    print()

if __name__ == '__main__':
    main()
