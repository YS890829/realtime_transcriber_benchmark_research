#!/usr/bin/env python3
"""
Google Drive Re-authentication with drive.file scope
Phase 10-1: ファイルリネーム権限付与
"""
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import os

# drive スコープで再認証（全ファイルアクセス）
SCOPES = ['https://www.googleapis.com/auth/drive']

def main():
    print("=" * 60)
    print("Google Drive 再認証")
    print("=" * 60)
    print(f"スコープ: {SCOPES[0]}")
    print("権限: ファイルの読み取り・書き込み・削除")
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
    print("Google Driveファイルの読み取り・書き込み権限が付与されました。")
    print()

if __name__ == '__main__':
    main()
