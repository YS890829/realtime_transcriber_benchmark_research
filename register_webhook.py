#!/usr/bin/env python3
"""
Google Drive Webhook登録スクリプト
"""

import os
import json
import uuid
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def register_webhook():
    """Google Drive Webhookを登録"""

    # ngrok URLを取得
    ngrok_url = os.getenv('NGROK_URL', 'https://9b43663db85d.ngrok-free.app')
    webhook_endpoint = f'{ngrok_url}/webhook'

    print(f'🔔 Registering webhook: {webhook_endpoint}')

    # 認証情報を読み込み
    creds = Credentials.from_authorized_user_file(
        'token.json',
        ['https://www.googleapis.com/auth/drive']
    )

    # Drive APIクライアントを作成
    service = build('drive', 'v3', credentials=creds)

    # 現在のページトークンを取得
    response = service.changes().getStartPageToken().execute()
    page_token = response.get('startPageToken')

    print(f'📌 Current page token: {page_token}')

    # Webhookを登録
    channel_id = str(uuid.uuid4())
    expiration_time = int((datetime.now() + timedelta(days=7)).timestamp() * 1000)

    body = {
        'id': channel_id,
        'type': 'web_hook',
        'address': webhook_endpoint,
        'expiration': expiration_time
    }

    try:
        result = service.changes().watch(
            pageToken=page_token,
            body=body
        ).execute()

        print('✅ Webhook registered successfully!')
        print(f'   Channel ID: {result["id"]}')
        print(f'   Resource ID: {result["resourceId"]}')
        print(f'   Expiration: {datetime.fromtimestamp(int(result["expiration"]) / 1000)}')

        # 設定をファイルに保存
        config = {
            'channel_id': result['id'],
            'resource_id': result['resourceId'],
            'expiration': result['expiration'],
            'webhook_url': webhook_endpoint,
            'page_token': page_token,
            'registered_at': datetime.now().isoformat()
        }

        with open('webhook_config.json', 'w') as f:
            json.dump(config, f, indent=2)

        print(f'✅ Config saved to webhook_config.json')

    except Exception as e:
        print(f'❌ Error registering webhook: {e}')
        raise

if __name__ == '__main__':
    register_webhook()
