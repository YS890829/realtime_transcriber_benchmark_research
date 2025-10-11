#!/usr/bin/env python3
"""
Google Drive Polling Monitor (Phase 5-2)
monitors My Drive/audio folder every 5 minutes and auto-transcribes new files
"""

import os
import time
from pathlib import Path
import subprocess
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io


# Constants
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
TOKEN_PATH = 'token.json'
PROCESSED_FILE = '.processed_drive_files.txt'
AUDIO_FOLDER_NAME = 'audio'  # My Drive/audio
POLL_INTERVAL = 300  # 5 minutes (300 seconds)
DOWNLOAD_DIR = Path('downloads')  # Local download directory (same as drive_download.py)


def get_drive_service():
    """authenticate with Google Drive API using existing token.json"""
    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # Refresh token if expired
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())

    if not creds or not creds.valid:
        raise Exception(f"Invalid credentials. Please run drive_download.py first to authenticate.")

    return build('drive', 'v3', credentials=creds)


def find_audio_folder(service):
    """find 'audio' folder in My Drive"""
    query = f"name='{AUDIO_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and 'root' in parents and trashed=false"

    results = service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name)'
    ).execute()

    files = results.get('files', [])

    if not files:
        raise Exception(f"Folder '{AUDIO_FOLDER_NAME}' not found in My Drive. Please create it first.")

    return files[0]['id']


def get_processed_files():
    """read processed file IDs from .processed_drive_files.txt"""
    if not os.path.exists(PROCESSED_FILE):
        return set()

    with open(PROCESSED_FILE, 'r') as f:
        return set(line.strip() for line in f if line.strip())


def mark_as_processed(file_id):
    """append file ID to .processed_drive_files.txt"""
    with open(PROCESSED_FILE, 'a') as f:
        f.write(f"{file_id}\n")


def list_audio_files(service, folder_id):
    """list all audio files in the audio folder"""
    query = f"'{folder_id}' in parents and trashed=false"

    results = service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name, mimeType)',
        orderBy='createdTime desc'
    ).execute()

    return results.get('files', [])


def download_file(service, file_id, file_name):
    """download file from Google Drive"""
    request = service.files().get_media(fileId=file_id)

    # Create download directory if not exists
    DOWNLOAD_DIR.mkdir(exist_ok=True)

    file_path = DOWNLOAD_DIR / file_name

    with io.FileIO(file_path, 'wb') as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"  Download progress: {int(status.progress() * 100)}%", end='\r')

    print()  # New line after progress
    return file_path


def transcribe_file(audio_path):
    """call transcribe_api.py to transcribe and summarize"""
    cmd = [
        'venv/bin/python',
        'transcribe_api.py',
        str(audio_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise Exception(f"Transcription failed: {result.stderr}")

    return result.stdout


def process_new_files(service, folder_id):
    """check for new files and process them"""
    processed_files = get_processed_files()
    audio_files = list_audio_files(service, folder_id)

    new_files = [f for f in audio_files if f['id'] not in processed_files]

    if not new_files:
        print("No new files found.")
        return

    print(f"\nFound {len(new_files)} new file(s):")

    for file_info in new_files:
        file_id = file_info['id']
        file_name = file_info['name']

        print(f"\n[Processing] {file_name} (ID: {file_id})")

        try:
            # Download
            print(f"[1/3] Downloading...")
            audio_path = download_file(service, file_id, file_name)
            print(f"  Saved to: {audio_path}")

            # Transcribe and summarize
            print(f"[2/3] Transcribing and summarizing...")
            output = transcribe_file(audio_path)
            print(output)

            # Mark as processed
            print(f"[3/3] Marking as processed...")
            mark_as_processed(file_id)
            print(f"  Added to {PROCESSED_FILE}")

            print(f"[✓] Completed: {file_name}")

        except Exception as e:
            print(f"[✗] Error processing {file_name}: {e}")
            continue


def monitor_loop():
    """main monitoring loop"""
    print("=" * 60)
    print("Google Drive Polling Monitor (Phase 5-2)")
    print("=" * 60)
    print(f"Monitoring: My Drive/{AUDIO_FOLDER_NAME}")
    print(f"Poll interval: {POLL_INTERVAL} seconds ({POLL_INTERVAL//60} minutes)")
    print(f"Processed files list: {PROCESSED_FILE}")
    print("Press Ctrl+C to stop\n")

    # Authenticate
    print("[Init] Authenticating with Google Drive...")
    service = get_drive_service()
    print("[Init] Authentication successful\n")

    # Find audio folder
    print(f"[Init] Finding '{AUDIO_FOLDER_NAME}' folder...")
    folder_id = find_audio_folder(service)
    print(f"[Init] Found folder ID: {folder_id}\n")

    print("[Init] Starting monitoring loop...\n")

    cycle = 0

    try:
        while True:
            cycle += 1
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[Cycle {cycle}] {timestamp} - Checking for new files...")

            try:
                process_new_files(service, folder_id)
            except Exception as e:
                print(f"[Error] {e}")

            print(f"\n[Sleep] Waiting {POLL_INTERVAL} seconds until next check...")
            print("-" * 60)
            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("\n\n[Stop] Monitoring stopped by user")
        print("=" * 60)


if __name__ == '__main__':
    monitor_loop()
