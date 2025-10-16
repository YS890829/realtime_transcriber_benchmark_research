#!/usr/bin/env python3
"""
Google Calendar Integration Module (Phase 11-1)
音声ファイル作成日のカレンダー予定を取得し、文字起こし内容とマッチング

使い方:
    from calendar_integration import get_events_for_file_date, match_event_with_transcript

    events = get_events_for_file_date('20251016')
    match_result = match_event_with_transcript(transcript_text, events)

機能:
- Google Calendar API認証（token.jsonにCalendar.readonly追加）
- 音声ファイル作成日の予定を全件取得
- LLMによる内容ベースの予定マッチング
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import google.generativeai as genai

# 環境変数読み込み
load_dotenv()

# 設定
TOKEN_PATH = 'token.json'
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/calendar.readonly'
]


def authenticate_calendar_service():
    """
    Google Calendar API認証
    既存のtoken.jsonを使用（Calendar.readonlyスコープ追加）

    Returns:
        Calendar APIサービスオブジェクト
    """
    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # トークンが無効または期限切れの場合、リフレッシュまたは再認証
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                print("✅ トークンをリフレッシュしました")
            except Exception as e:
                print(f"⚠️  トークンリフレッシュ失敗: {e}")
                print("新しいスコープが必要なため、再認証します...")
                creds = None  # 再認証フローに進む

        # 初回認証またはリフレッシュ失敗時
        if not creds:
            credentials_file = os.getenv('CREDENTIALS_FILE', 'credentials.json')
            if not os.path.exists(credentials_file):
                print(f"❌ {credentials_file}が見つかりません")
                print("Google Cloud Consoleから認証情報をダウンロードしてください")
                return None

            print("🔐 OAuth2認証フローを開始します...")
            print("ブラウザが開きます。Googleアカウントでログインしてください。")
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
            print("✅ 認証成功")

        # トークンを保存
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())
            print(f"✅ トークンを保存しました: {TOKEN_PATH}")

    try:
        service = build('calendar', 'v3', credentials=creds)
        return service
    except HttpError as error:
        print(f"❌ Calendar API初期化エラー: {error}")
        return None


def get_file_date(file_path: str) -> str:
    """
    音声ファイルの作成日をYYYYMMDD形式で取得

    優先順位:
    1. ファイル名から抽出（20251016_description.m4a）
    2. st_ctimeから取得

    Args:
        file_path: 音声ファイルパス

    Returns:
        YYYYMMDD形式の日付文字列
    """
    filename = Path(file_path).stem

    # パターン1: YYYYMMDD_description
    match = re.match(r'^(\d{8})_', filename)
    if match:
        date_str = match.group(1)
        print(f"📅 ファイル名から日付取得: {date_str}")
        return date_str

    # パターン2: st_ctime
    ctime = os.path.getctime(file_path)
    date_str = datetime.fromtimestamp(ctime).strftime('%Y%m%d')
    print(f"📅 ファイル作成日時から日付取得: {date_str}")
    return date_str


def get_events_for_file_date(file_date: str, calendar_id: str = 'primary') -> list:
    """
    指定日の予定を全件取得

    Args:
        file_date: YYYYMMDD形式の日付
        calendar_id: カレンダーID（デフォルト: 'primary'）

    Returns:
        その日の予定リスト（タイトル、開始時刻、終了時刻、メモ、参加者）
    """
    service = authenticate_calendar_service()
    if not service:
        print("⚠️  Calendar API認証に失敗しました")
        return []

    try:
        # YYYYMMDD → datetime変換
        date_obj = datetime.strptime(file_date, '%Y%m%d')
        time_min = date_obj.replace(hour=0, minute=0, second=0).isoformat() + 'Z'
        time_max = date_obj.replace(hour=23, minute=59, second=59).isoformat() + 'Z'

        print(f"🔍 {file_date}の予定を検索中...")

        # Calendar API呼び出し
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        if not events:
            print(f"📭 {file_date}には予定がありません")
            return []

        print(f"✅ {len(events)}件の予定を取得しました")

        # デバッグ出力
        for i, event in enumerate(events):
            start = event.get('start', {}).get('dateTime', event.get('start', {}).get('date', ''))
            summary = event.get('summary', '（タイトルなし）')
            print(f"  {i+1}. {summary} ({start})")

        return events

    except HttpError as error:
        print(f"❌ Calendar API呼び出しエラー: {error}")
        return []
    except Exception as e:
        print(f"❌ 予定取得エラー: {e}")
        return []


def format_events(events: list) -> str:
    """
    予定リストをLLM入力用フォーマットに変換

    Args:
        events: Calendar APIから取得した予定リスト

    Returns:
        フォーマット済み文字列
    """
    if not events:
        return "（予定なし）"

    formatted = []
    for i, event in enumerate(events):
        summary = event.get('summary', '（タイトルなし）')
        start = event.get('start', {}).get('dateTime', event.get('start', {}).get('date', ''))
        end = event.get('end', {}).get('dateTime', event.get('end', {}).get('date', ''))
        description = event.get('description', '')

        # 参加者リスト
        attendees = event.get('attendees', [])
        attendees_str = ', '.join([a.get('email', '') for a in attendees]) if attendees else 'なし'

        formatted.append(f"""
予定{i+1}:
- タイトル: {summary}
- 開始: {start}
- 終了: {end}
- メモ: {description if description else 'なし'}
- 参加者: {attendees_str}
""")

    return '\n'.join(formatted)


def match_event_with_transcript(transcript_text: str, calendar_events: list) -> dict:
    """
    文字起こし内容とカレンダー予定をLLMでマッチング

    Args:
        transcript_text: 文字起こし全文
        calendar_events: Calendar APIから取得した予定リスト

    Returns:
        {
            "matched_event": {...} or None,
            "confidence_score": 0.0-1.0,
            "reasoning": "判断理由"
        }
    """
    if not calendar_events:
        return {
            "matched_event": None,
            "confidence_score": 0.0,
            "reasoning": "予定なし"
        }

    # Gemini API設定（既存の仕組みに合わせる）
    use_paid = os.getenv('USE_PAID_TIER', 'false').lower() == 'true'
    if use_paid:
        api_key = os.getenv('GEMINI_API_KEY_PAID')
        if not api_key:
            print("❌ GEMINI_API_KEY_PAIDが設定されていません")
            return {
                "matched_event": None,
                "confidence_score": 0.0,
                "reasoning": "API KEY未設定"
            }
    else:
        api_key = os.getenv('GEMINI_API_KEY_FREE')
        if not api_key:
            print("❌ GEMINI_API_KEY_FREEが設定されていません")
            return {
                "matched_event": None,
                "confidence_score": 0.0,
                "reasoning": "API KEY未設定"
            }

    genai.configure(api_key=api_key)

    # 文字起こし全文（長い場合は冒頭3000文字のみ）
    transcript_sample = transcript_text[:3000] if len(transcript_text) > 3000 else transcript_text

    # プロンプト作成
    prompt = f"""以下の音声文字起こし内容と、その日のGoogleカレンダー予定を照合してください。

【文字起こし内容】
{transcript_sample}

【その日の予定一覧】
{format_events(calendar_events)}

【タスク】
1. 文字起こし内容が、どの予定に該当するか判断してください
2. 複数の候補がある場合、最も内容が合致するものを1つ選んでください
3. 該当する予定がない場合は「該当なし」と判断してください
4. 信頼度スコア（0.0-1.0）を算出してください（0.7以上を推奨）

【判断基準】
- タイトルや予定メモに含まれるキーワードと文字起こし内容の一致度
- 参加者名の言及
- トピックの類似性

【出力形式（JSON）】
{{
  "matched_event_index": 整数インデックス（0始まり）or null,
  "confidence_score": 0.0-1.0,
  "reasoning": "判断理由（日本語で詳しく）"
}}

**重要**: 必ずJSON形式のみを出力してください。他の説明文は不要です。
"""

    try:
        # Gemini 2.0 Flash（軽量・安価）
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        response = model.generate_content(prompt)

        # JSONパース
        response_text = response.text.strip()

        # Markdown code blockを削除
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
            response_text = response_text.strip()

        result = json.loads(response_text)

        # 結果検証
        matched_index = result.get('matched_event_index')
        confidence = result.get('confidence_score', 0.0)
        reasoning = result.get('reasoning', '')

        print(f"\n🤖 予定マッチング結果:")
        print(f"   信頼度: {confidence:.2f}")
        print(f"   理由: {reasoning}")

        # 信頼度が0.7以上かつ有効なインデックスの場合のみマッチとする
        if matched_index is not None and 0 <= matched_index < len(calendar_events) and confidence >= 0.7:
            matched_event = calendar_events[matched_index]
            print(f"   ✅ マッチした予定: {matched_event.get('summary', '（タイトルなし）')}")
            return {
                "matched_event": matched_event,
                "confidence_score": confidence,
                "reasoning": reasoning
            }
        else:
            print(f"   ⚠️  該当する予定なし（信頼度が低い、またはインデックスが無効）")
            return {
                "matched_event": None,
                "confidence_score": confidence,
                "reasoning": reasoning
            }

    except json.JSONDecodeError as e:
        print(f"❌ JSON解析エラー: {e}")
        print(f"レスポンス: {response.text[:500]}")
        return {
            "matched_event": None,
            "confidence_score": 0.0,
            "reasoning": f"JSON解析エラー: {str(e)}"
        }
    except Exception as e:
        print(f"❌ 予定マッチングエラー: {e}")
        return {
            "matched_event": None,
            "confidence_score": 0.0,
            "reasoning": f"エラー: {str(e)}"
        }


if __name__ == '__main__':
    # テスト用
    print("=== Calendar Integration Test ===")

    # テスト1: 認証
    service = authenticate_calendar_service()
    if service:
        print("✅ Calendar API認証成功")

    # テスト2: 今日の予定取得
    today = datetime.now().strftime('%Y%m%d')
    events = get_events_for_file_date(today)

    if events:
        print(f"\n今日の予定（{len(events)}件）:")
        print(format_events(events))
