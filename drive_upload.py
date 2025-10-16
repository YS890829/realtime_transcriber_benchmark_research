#!/usr/bin/env python3
"""
Phase 10-4: Google Drive Upload
文字起こし結果JSONをGoogle Driveへアップロード
"""

import os
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
import time

# Load environment variables
load_dotenv()

# Constants
TOKEN_PATH = os.getenv('TOKEN_PATH', 'token.json')
SCOPES = [os.getenv('GOOGLE_DRIVE_SCOPES', 'https://www.googleapis.com/auth/drive')]
UPLOAD_FOLDER_NAME = os.getenv('DRIVE_UPLOAD_FOLDER', 'transcriptions')
UPLOAD_LOG_FILE = os.getenv('UPLOAD_LOG_FILE', '.upload_log.jsonl')


def authenticate_drive():
    """
    Google Drive認証（既存のtoken.jsonを再利用）

    Returns:
        Google Drive APIサービスオブジェクト
    """
    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_PATH, 'w') as token:
                token.write(creds.to_json())
        else:
            raise Exception(f"❌ 認証エラー: {TOKEN_PATH} が無効です。再認証が必要です。")

    service = build('drive', 'v3', credentials=creds)
    return service


def get_or_create_folder(service, folder_name):
    """
    指定されたフォルダを取得、存在しない場合は作成

    Args:
        service: Google Drive APIサービス
        folder_name: フォルダ名

    Returns:
        フォルダID
    """
    # フォルダ検索
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name)'
    ).execute()

    folders = results.get('files', [])

    if folders:
        folder_id = folders[0]['id']
        print(f"✅ フォルダ '{folder_name}' を確認（ID: {folder_id}）")
        return folder_id

    # フォルダ作成
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }

    folder = service.files().create(
        body=file_metadata,
        fields='id'
    ).execute()

    folder_id = folder.get('id')
    print(f"✅ フォルダ '{folder_name}' を作成（ID: {folder_id}）")
    return folder_id


def upload_file_to_drive(service, file_path, folder_id, max_retries=3):
    """
    ファイルをGoogle Driveにアップロード

    Args:
        service: Google Drive APIサービス
        file_path: アップロードするファイルパス
        folder_id: アップロード先フォルダID
        max_retries: 最大リトライ回数

    Returns:
        アップロードされたファイルID（失敗時はNone）
    """
    file_path = Path(file_path)
    file_name = file_path.name

    # 既存ファイルチェック（同名ファイルが存在する場合）
    query = f"name='{file_name}' and '{folder_id}' in parents and trashed=false"
    results = service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name)'
    ).execute()

    existing_files = results.get('files', [])

    if existing_files:
        # 同名ファイルが存在する場合はタイムスタンプ付きリネーム
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name_without_ext = file_path.stem
        extension = file_path.suffix
        file_name = f"{name_without_ext}_{timestamp}{extension}"
        print(f"ℹ️  同名ファイル検出、リネームしてアップロード: {file_name}")

    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }

    media = MediaFileUpload(
        str(file_path),
        mimetype='application/json',
        resumable=True
    )

    # リトライロジック
    for attempt in range(max_retries):
        try:
            uploaded_file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink'
            ).execute()

            file_id = uploaded_file.get('id')
            web_link = uploaded_file.get('webViewLink')
            print(f"✅ アップロード成功: {file_name}")
            print(f"   URL: {web_link}")

            return file_id

        except HttpError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"⚠️  アップロード失敗（試行 {attempt + 1}/{max_retries}）、{wait_time}秒後にリトライ...")
                time.sleep(wait_time)
            else:
                print(f"❌ アップロード失敗（最大リトライ回数超過）: {e}")
                return None
        except Exception as e:
            print(f"❌ 予期しないエラー: {e}")
            return None

    return None


def log_upload(file_path, drive_file_id, status, error_message=None):
    """
    アップロードログをJSONL形式で記録

    Args:
        file_path: アップロードしたファイルパス
        drive_file_id: Google DriveファイルID
        status: アップロード状態（"success" / "failed"）
        error_message: エラーメッセージ（失敗時のみ）
    """
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "file": Path(file_path).name,
        "drive_id": drive_file_id,
        "status": status,
        "size_mb": round(Path(file_path).stat().st_size / (1024 * 1024), 2)
    }

    if error_message:
        log_entry["error"] = error_message

    with open(UPLOAD_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')


def upload_transcription_results(json_path):
    """
    文字起こし結果JSONをGoogle Driveにアップロード

    Args:
        json_path: アップロードする*_structured.jsonのパス

    Returns:
        bool: アップロード成功時True、失敗時False
    """
    try:
        # ファイル存在確認
        if not Path(json_path).exists():
            print(f"⚠️  ファイルが見つかりません: {json_path}")
            return False

        print(f"\n📤 Google Driveへアップロード中...")
        print(f"   ファイル: {Path(json_path).name}")

        # Google Drive認証
        service = authenticate_drive()

        # transcriptionsフォルダ取得・作成
        folder_id = get_or_create_folder(service, UPLOAD_FOLDER_NAME)

        # ファイルアップロード
        drive_file_id = upload_file_to_drive(service, json_path, folder_id)

        if drive_file_id:
            # 成功ログ記録
            log_upload(json_path, drive_file_id, "success")
            print(f"📱 スマホからアクセス: Google Drive → マイドライブ → {UPLOAD_FOLDER_NAME}")
            return True
        else:
            # 失敗ログ記録
            log_upload(json_path, None, "failed", "Upload failed after retries")
            return False

    except Exception as e:
        print(f"❌ Google Driveアップロードエラー: {e}")
        log_upload(json_path, None, "failed", str(e))
        return False


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("使い方: python drive_upload.py <json_file_path>")
        sys.exit(1)

    json_path = sys.argv[1]
    success = upload_transcription_results(json_path)

    if success:
        print("\n✅ Google Driveアップロード完了")
        sys.exit(0)
    else:
        print("\n❌ Google Driveアップロード失敗")
        sys.exit(1)
