#!/usr/bin/env python3
"""
Google Docs Export Module (Phase 10-4 拡張)
JSONファイルからモバイルフレンドリーなGoogle Docsを生成

使い方:
    from drive_docs_export import export_json_to_docs
    export_json_to_docs('path/to/file_structured.json')

機能:
- JSONから読みやすいGoogle Docs作成
- サマリ・全文・メタデータをフォーマット
- 話者識別付きセグメント表示
- transcriptionsフォルダへ自動配置
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# 環境変数読み込み
load_dotenv()

# 設定
FOLDER_NAME = os.getenv('DRIVE_UPLOAD_FOLDER', 'transcriptions')
TOKEN_PATH = 'token.json'
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/documents'
]


def authenticate_services():
    """
    Google Drive + Docs API認証
    既存のtoken.jsonを使用
    """
    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # トークンが無効または期限切れの場合、リフレッシュ
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # 更新したトークンを保存
            with open(TOKEN_PATH, 'w') as token:
                token.write(creds.to_json())
        else:
            raise ValueError("有効なtoken.jsonが見つかりません。drive_download.pyで認証を完了してください。")

    drive_service = build('drive', 'v3', credentials=creds)
    docs_service = build('docs', 'v1', credentials=creds)

    return drive_service, docs_service


def get_transcriptions_folder_id(drive_service):
    """
    transcriptionsフォルダIDを取得（既存のdrive_upload.pyと同じロジック）
    """
    query = f"name='{FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    folders = results.get('files', [])

    if folders:
        return folders[0]['id']
    else:
        # フォルダが存在しない場合は作成
        file_metadata = {
            'name': FOLDER_NAME,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = drive_service.files().create(body=file_metadata, fields='id').execute()
        print(f"✅ フォルダ '{FOLDER_NAME}' を作成（ID: {folder['id']}）")
        return folder['id']


def read_json_file(json_path):
    """
    JSONファイルを読み込み
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def create_google_doc(docs_service, title):
    """
    空のGoogle Documentを作成
    """
    body = {
        'title': title
    }
    doc = docs_service.documents().create(body=body).execute()
    return doc['documentId']


def build_document_requests(data):
    """
    JSONデータからGoogle Docs batchUpdate requestsを構築

    ドキュメント構成:
    ━━━━━━━━━━━━━━━━━
    📊 サマリ
    ━━━━━━━━━━━━━━━━━
    要約テキスト...

    ━━━━━━━━━━━━━━━━━
    📝 全文
    ━━━━━━━━━━━━━━━━━
    Speaker 1 (00:15)
    発言内容...

    ━━━━━━━━━━━━━━━━━
    ℹ️ メタデータ
    ━━━━━━━━━━━━━━━━━
    • 文字起こし日時: ...
    • 文字数: ...
    """
    requests = []
    current_index = 1  # ドキュメントの先頭は1

    # セクション1: サマリ
    summary_section = "━━━━━━━━━━━━━━━━━\n📊 サマリ\n━━━━━━━━━━━━━━━━━\n\n"
    summary_data = data.get('summary', {})

    # Phase 11-1以降: summaryはdict形式
    if isinstance(summary_data, dict):
        summary_text = summary_data.get('summary', '')
        topics = summary_data.get('topics', [])
        action_items = summary_data.get('action_items', [])
        keywords = summary_data.get('keywords', [])

        if summary_text:
            summary_section += f"{summary_text}\n\n"

        if topics:
            summary_section += "【主要トピック】\n"
            for topic in topics:
                summary_section += f"• {topic}\n"
            summary_section += "\n"

        if action_items:
            summary_section += "【アクションアイテム】\n"
            for item in action_items:
                summary_section += f"• {item}\n"
            summary_section += "\n"

        if keywords:
            summary_section += f"【キーワード】\n{', '.join(keywords)}\n\n"

    # 旧形式: summaryは文字列
    elif isinstance(summary_data, str):
        if summary_data:
            summary_section += summary_data + "\n\n"
        else:
            summary_section += "要約が生成されませんでした。\n\n"

    # 要約情報なし
    else:
        summary_section += "要約情報なし\n\n"

    requests.append({
        'insertText': {
            'location': {'index': current_index},
            'text': summary_section
        }
    })

    summary_end_index = current_index + len(summary_section)

    # サマリ見出しのスタイル適用
    requests.append({
        'updateParagraphStyle': {
            'range': {
                'startIndex': current_index + len("━━━━━━━━━━━━━━━━━\n"),
                'endIndex': current_index + len("━━━━━━━━━━━━━━━━━\n📊 サマリ\n")
            },
            'paragraphStyle': {
                'namedStyleType': 'HEADING_1'
            },
            'fields': 'namedStyleType'
        }
    })

    current_index = summary_end_index

    # セクション2: 全文（話者別セグメント）
    transcript_section = "━━━━━━━━━━━━━━━━━\n📝 全文\n━━━━━━━━━━━━━━━━━\n\n"

    segments = data.get('segments', [])
    if segments:
        for seg in segments:
            speaker = seg.get('speaker', 'Unknown')
            timestamp = seg.get('timestamp', '00:00')
            text = seg.get('text', '')
            transcript_section += f"{speaker} ({timestamp})\n{text}\n\n"
    else:
        # segmentsがない場合はfull_textを使用
        full_text = data.get('full_text', '文字起こしテキストなし')
        transcript_section += full_text + "\n\n"

    requests.append({
        'insertText': {
            'location': {'index': current_index},
            'text': transcript_section
        }
    })

    transcript_heading_start = current_index + len("━━━━━━━━━━━━━━━━━\n")
    transcript_heading_end = current_index + len("━━━━━━━━━━━━━━━━━\n📝 全文\n")

    # 全文見出しのスタイル適用
    requests.append({
        'updateParagraphStyle': {
            'range': {
                'startIndex': transcript_heading_start,
                'endIndex': transcript_heading_end
            },
            'paragraphStyle': {
                'namedStyleType': 'HEADING_1'
            },
            'fields': 'namedStyleType'
        }
    })

    current_index += len(transcript_section)

    # セクション3: メタデータ
    metadata_section = "━━━━━━━━━━━━━━━━━\nℹ️ メタデータ\n━━━━━━━━━━━━━━━━━\n\n"

    metadata = data.get('metadata', {})
    transcription_meta = metadata.get('transcription', {})
    file_meta = metadata.get('file', {})

    # メタデータ項目
    metadata_items = [
        f"• 文字起こし日時: {transcription_meta.get('transcribed_at', 'N/A')}",
        f"• 言語: {transcription_meta.get('language', 'N/A')}",
        f"• 文字数: {transcription_meta.get('char_count', 0):,}",
        f"• 単語数: {transcription_meta.get('word_count', 0):,}",
        f"• セグメント数: {transcription_meta.get('segment_count', 0)}",
        f"• ファイル名: {file_meta.get('file_name', 'N/A')}",
        f"• ファイルサイズ: {file_meta.get('file_size_bytes', 0) / 1024 / 1024:.2f} MB",
    ]

    # 音声長がある場合
    if file_meta.get('duration_seconds'):
        duration = file_meta['duration_seconds']
        metadata_items.append(f"• 音声長: {duration:.1f}秒 ({duration/60:.1f}分)")

    metadata_section += "\n".join(metadata_items) + "\n"

    requests.append({
        'insertText': {
            'location': {'index': current_index},
            'text': metadata_section
        }
    })

    metadata_heading_start = current_index + len("━━━━━━━━━━━━━━━━━\n")
    metadata_heading_end = current_index + len("━━━━━━━━━━━━━━━━━\nℹ️ メタデータ\n")

    # メタデータ見出しのスタイル適用
    requests.append({
        'updateParagraphStyle': {
            'range': {
                'startIndex': metadata_heading_start,
                'endIndex': metadata_heading_end
            },
            'paragraphStyle': {
                'namedStyleType': 'HEADING_2'
            },
            'fields': 'namedStyleType'
        }
    })

    return requests


def export_json_to_docs(json_path, max_retries=3):
    """
    JSONファイルからGoogle Docsを作成してtranscriptionsフォルダへ配置

    Args:
        json_path: 入力JSONファイルパス
        max_retries: リトライ回数

    Returns:
        bool: 成功時True、失敗時False
    """
    json_path = Path(json_path)

    if not json_path.exists():
        print(f"⚠️  ファイルが見つかりません: {json_path}")
        return False

    print(f"\n📄 Google Docs作成中...")
    print(f"   ファイル: {json_path.name}")

    try:
        # 認証
        drive_service, docs_service = authenticate_services()

        # JSONデータ読み込み
        data = read_json_file(json_path)

        # ドキュメントタイトル（.jsonを除去）
        doc_title = json_path.stem.replace('_structured', '')

        # Google Docs作成
        doc_id = create_google_doc(docs_service, doc_title)
        print(f"✅ ドキュメント作成: {doc_title}")

        # コンテンツ挿入リクエスト構築
        requests = build_document_requests(data)

        # batchUpdate実行（リトライロジック付き）
        for attempt in range(max_retries):
            try:
                docs_service.documents().batchUpdate(
                    documentId=doc_id,
                    body={'requests': requests}
                ).execute()
                print(f"✅ コンテンツ挿入完了")
                break
            except HttpError as e:
                if e.resp.status == 429 and attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 2
                    print(f"⚠️  Rate limit（試行 {attempt + 1}/{max_retries}）: {wait_time}秒待機...")
                    time.sleep(wait_time)
                else:
                    raise

        # transcriptionsフォルダへ移動
        folder_id = get_transcriptions_folder_id(drive_service)

        drive_service.files().update(
            fileId=doc_id,
            addParents=folder_id,
            fields='id, parents'
        ).execute()

        print(f"✅ Google Docs作成完了: {doc_title}")
        print(f"   URL: https://docs.google.com/document/d/{doc_id}/edit")
        print(f"📱 スマホからアクセス: Google Drive → マイドライブ → {FOLDER_NAME}")

        return True

    except HttpError as e:
        print(f"❌ Google API エラー: {e}")
        return False
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("使い方: python drive_docs_export.py <JSONファイルパス>")
        print("例: python drive_docs_export.py downloads/test_structured.json")
        sys.exit(1)

    json_path = sys.argv[1]
    success = export_json_to_docs(json_path)

    if success:
        print("\n✅ Google Docs エクスポート完了")
    else:
        print("\n❌ Google Docs エクスポート失敗")
        sys.exit(1)
