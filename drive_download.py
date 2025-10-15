#!/usr/bin/env python3
"""
Google Drive手動ダウンロード＆文字起こしスクリプト（Phase 5-1）

使い方:
  python drive_download.py <file_id>

機能:
  - Google Drive OAuth 2.0認証
  - 指定したfile_idのファイルをダウンロード
  - transcribe_api.pyを呼び出して文字起こし・要約
"""

import os
import sys
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import subprocess

# Google Drive API スコープ（読み取り専用）
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# 認証ファイル
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'

# ダウンロード先フォルダ
DOWNLOAD_DIR = Path(__file__).parent / 'downloads'


def authenticate_drive():
    """
    Google Drive認証を実行

    初回実行時:
      - ブラウザが開き、Google認証画面が表示される
      - アカウント選択→権限許可
      - token.jsonが自動生成される

    2回目以降:
      - token.jsonを使用して自動認証（ブラウザ不要）

    戻り値:
      Google Drive APIサービスオブジェクト
    """
    creds = None

    # token.jsonが存在する場合は読み込む
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # 認証情報が無効または存在しない場合
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # トークンをリフレッシュ
            print("🔄 認証トークンを更新中...")
            creds.refresh(Request())
        else:
            # 初回認証フロー
            print("🔐 初回認証を開始します...")
            print("ブラウザが開きます。Googleアカウントでログインして権限を許可してください。")
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            print("✅ 認証成功！")

        # token.jsonに保存
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
        print(f"📝 認証情報を {TOKEN_FILE} に保存しました")

    # Google Drive APIサービスを構築
    service = build('drive', 'v3', credentials=creds)
    return service


def download_file(service, file_id, destination_path):
    """
    Google Driveからファイルをダウンロード

    引数:
      service: Google Drive APIサービスオブジェクト
      file_id: ダウンロードするファイルのID
      destination_path: ダウンロード先のパス
    """
    try:
        # ファイルメタデータを取得
        file_metadata = service.files().get(fileId=file_id, fields='name, mimeType').execute()
        file_name = file_metadata.get('name')

        print(f"📥 ダウンロード開始: {file_name}")

        # ファイルをダウンロード
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"  ダウンロード進捗: {int(status.progress() * 100)}%")

        # ファイルに書き込み
        with open(destination_path, 'wb') as f:
            fh.seek(0)
            f.write(fh.read())

        print(f"✅ ダウンロード完了: {destination_path}")
        return file_name

    except Exception as e:
        print(f"❌ ダウンロードエラー: {e}")
        sys.exit(1)


def main():
    """メイン処理"""
    # コマンドライン引数チェック
    if len(sys.argv) != 2:
        print("使い方: python drive_download.py <file_id>")
        print("\nfile_idの取得方法:")
        print("  1. Google Driveでファイルを右クリック→「リンクを取得」")
        print("  2. URLの /d/XXXXX/ の XXXXX 部分がfile_id")
        print("  例: https://drive.google.com/file/d/1a2b3c4d5e/view")
        print("      → file_id は 1a2b3c4d5e")
        sys.exit(1)

    file_id = sys.argv[1]

    print("=" * 60)
    print("Google Drive手動ダウンロード＆文字起こし")
    print("=" * 60)

    # Google Drive認証
    print("\n📁 Google Driveに接続中...")
    service = authenticate_drive()
    print("✅ Google Drive接続成功")

    # ダウンロード先フォルダを作成
    DOWNLOAD_DIR.mkdir(exist_ok=True)

    # ファイルをダウンロード
    print(f"\n📥 ファイルID: {file_id}")
    destination = DOWNLOAD_DIR / f"temp_{file_id}"
    file_name = download_file(service, file_id, destination)

    # 元のファイル名にリネーム
    final_destination = DOWNLOAD_DIR / file_name
    destination.rename(final_destination)

    # structured_transcribe.pyを呼び出し（Gemini Audio API）
    print(f"\n🎙️ 文字起こし開始: {file_name}")
    try:
        result = subprocess.run(
            [sys.executable, 'structured_transcribe.py', str(final_destination)],
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        print("✅ 文字起こし完了！")
    except subprocess.CalledProcessError as e:
        print(f"❌ 文字起こしエラー:")
        print(e.stderr)
        sys.exit(1)

    print("\n" + "=" * 60)
    print("🎉 全処理完了！")
    print("=" * 60)


if __name__ == "__main__":
    main()
