#!/usr/bin/env python3
"""
Google Drive Webhook Server (Modified for My Drive root)
Real-time file detection using Google Drive Push Notifications
Monitors My Drive root for audio files
"""

import os
import subprocess
from pathlib import Path
from fastapi import FastAPI, Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import json
from datetime import datetime, timedelta
import threading
from dotenv import load_dotenv
from filelock import FileLock, Timeout
import time

# Load environment variables
load_dotenv()

# Constants from environment variables
SCOPES = [os.getenv('GOOGLE_DRIVE_SCOPES', 'https://www.googleapis.com/auth/drive.readonly')]
TOKEN_PATH = os.getenv('TOKEN_PATH', 'token.json')
PROCESSED_FILE = os.getenv('PROCESSED_FILE', '.processed_drive_files.txt')
DOWNLOAD_DIR = Path(os.getenv('DOWNLOAD_DIR', 'downloads'))
PAGE_TOKEN_FILE = '.start_page_token.txt'
CHANNEL_FILE = '.channel_info.json'

# Lock directory for preventing duplicate processing
LOCK_DIR = Path('.processing_locks')
LOCK_DIR.mkdir(exist_ok=True)

# Webhook notification channel will expire after this duration
CHANNEL_EXPIRATION_HOURS = int(os.getenv('CHANNEL_EXPIRATION_HOURS', '24'))


def cleanup_old_locks():
    """Remove stale lock files on startup (handles abnormal termination cases)"""
    current_time = time.time()
    stale_threshold = 1800  # 30 minutes in seconds

    for lock_file in LOCK_DIR.glob('*.lock'):
        try:
            # Check if lock file is older than threshold
            if current_time - lock_file.stat().st_mtime > stale_threshold:
                print(f"[Cleanup] Removing stale lock: {lock_file.name}")
                lock_file.unlink(missing_ok=True)
        except Exception as e:
            print(f"[Warning] Failed to clean up {lock_file.name}: {e}")


def get_drive_service():
    """Get authenticated Google Drive service"""
    if not os.path.exists(TOKEN_PATH):
        raise Exception(f"Token not found. Please run drive_download.py first to authenticate.")

    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    return build('drive', 'v3', credentials=creds)


def get_root_folder_id():
    """Return My Drive root folder ID"""
    return 'root'


def get_start_page_token(service):
    """Get or retrieve start page token for changes API"""
    if os.path.exists(PAGE_TOKEN_FILE):
        with open(PAGE_TOKEN_FILE, 'r') as f:
            return f.read().strip()

    # Get initial page token
    response = service.changes().getStartPageToken().execute()
    token = response.get('startPageToken')

    # Save it
    with open(PAGE_TOKEN_FILE, 'w') as f:
        f.write(token)

    return token


def save_page_token(token):
    """Save page token for next changes check"""
    with open(PAGE_TOKEN_FILE, 'w') as f:
        f.write(token)


def get_processed_files():
    """Read processed file IDs"""
    if not os.path.exists(PROCESSED_FILE):
        return set()

    with open(PROCESSED_FILE, 'r') as f:
        return set(line.strip() for line in f if line.strip())


def mark_as_processed(file_id):
    """Mark file as processed (with duplicate check)"""
    processed = get_processed_files()
    if file_id not in processed:
        with open(PROCESSED_FILE, 'a') as f:
            f.write(f"{file_id}\n")


def download_file(service, file_id, file_name):
    """Download file from Google Drive"""
    request = service.files().get_media(fileId=file_id)

    DOWNLOAD_DIR.mkdir(exist_ok=True)
    file_path = DOWNLOAD_DIR / file_name

    with io.FileIO(file_path, 'wb') as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()

    return file_path


def transcribe_file(audio_path):
    """Call structured_transcribe.py to transcribe (Gemini Audio API)"""
    cmd = [
        'venv/bin/python',
        'structured_transcribe.py',
        str(audio_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    # Always log subprocess output for debugging (flush=True for thread safety)
    print(f"[Debug] Transcription subprocess completed", flush=True)
    print(f"[Debug] Exit code: {result.returncode}", flush=True)

    if result.stdout:
        print(f"[Debug] STDOUT:\n{result.stdout}", flush=True)

    if result.stderr:
        print(f"[Debug] STDERR:\n{result.stderr}", flush=True)

    if result.returncode != 0:
        error_msg = f"Transcription failed with exit code {result.returncode}\n"
        error_msg += f"STDERR: {result.stderr}\n"
        error_msg += f"STDOUT: {result.stdout}"
        print(f"[Error] {error_msg}", flush=True)
        raise Exception(error_msg)

    return result.stdout


def process_new_files(service, folder_id='root'):
    """Process new audio files in My Drive root"""
    print(f"[Debug] process_new_files called with folder_id={folder_id}", flush=True)
    processed_files = get_processed_files()
    print(f"[Debug] Loaded {len(processed_files)} processed files", flush=True)

    # Get all audio files in My Drive root
    query = f"'{folder_id}' in parents and mimeType contains 'audio/' and trashed=false"
    print(f"[Debug] Query: {query}", flush=True)
    results = service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name, mimeType)',
        orderBy='createdTime desc'
    ).execute()

    audio_files = results.get('files', [])
    print(f"[Debug] Found {len(audio_files)} total audio files", flush=True)
    new_files = [f for f in audio_files if f['id'] not in processed_files]
    print(f"[Debug] Found {len(new_files)} new files after filtering", flush=True)

    if not new_files:
        print("[Debug] No new files to process, returning", flush=True)
        return

    print(f"\n[Webhook] Found {len(new_files)} new file(s)", flush=True)

    for file_info in new_files:
        file_id = file_info['id']
        file_name = file_info['name']

        # Lock file path for this specific file
        lock_path = LOCK_DIR / f"{file_id}.lock"
        lock = FileLock(lock_path, timeout=1)

        try:
            # Try to acquire lock (non-blocking with 0.1s timeout)
            with lock.acquire(timeout=0.1):
                print(f"\n[Processing] {file_name} (ID: {file_id})", flush=True)

                try:
                    # Download
                    print(f"[1/3] Downloading...", flush=True)
                    audio_path = download_file(service, file_id, file_name)
                    print(f"  Saved to: {audio_path}", flush=True)

                    # Transcribe
                    print(f"[2/3] Transcribing and summarizing...", flush=True)
                    output = transcribe_file(audio_path)
                    print(output, flush=True)

                    # Mark as processed (before renaming, to prevent duplicate processing)
                    print(f"[3/3] Marking as processed...", flush=True)
                    mark_as_processed(file_id)
                    print(f"  Added to {PROCESSED_FILE}", flush=True)

                    # [Phase 10-1] Local rename is handled by structured_transcribe.py
                    # [Phase 10-2] Google Drive file will be deleted, so no need to rename on cloud

                    # [Phase 10-2] Auto-delete cloud files (after transcription completed)
                    # Always delete cloud files after successful transcription
                    try:
                        from cloud_file_manager import (
                            SafeDeletionValidator,
                            delete_gdrive_file,
                            log_deletion,
                            get_file_size_mb
                        )

                        # Find the most recent structured JSON file
                        json_files = list(audio_path.parent.glob("*_structured.json"))
                        if json_files:
                            # Sort by modification time (newest first)
                            json_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                            latest_json = json_files[0]

                            print(f"[Delete] Validating JSON integrity: {latest_json.name}", flush=True)

                            # Validate JSON integrity before deletion
                            validator = SafeDeletionValidator(latest_json)
                            validation_passed = validator.validate()
                            validation_results = validator.get_validation_details()

                            if validation_passed:
                                print(f"[Delete] ✅ Validation passed, deleting cloud file...", flush=True)

                                # Get file size for logging
                                file_size_mb = get_file_size_mb(service, file_id)

                                # Delete from Google Drive
                                deleted = False
                                error = None
                                try:
                                    delete_gdrive_file(service, file_id, file_name)
                                    deleted = True
                                    print(f"  ✅ Google Drive file deleted: {file_id}", flush=True)
                                except Exception as delete_error:
                                    error = str(delete_error)
                                    print(f"  ❌ Deletion failed: {error}", flush=True)

                                # Log deletion event
                                log_deletion(
                                    file_info={
                                        'file_id': file_id,
                                        'file_name': file_name,
                                        'original_name': file_name,
                                        'file_size_mb': file_size_mb,
                                        'json_path': latest_json
                                    },
                                    validation_results=validation_results,
                                    deleted=deleted,
                                    error=error
                                )

                            else:
                                print(f"[Delete] ❌ Validation failed, keeping cloud file", flush=True)
                                print(f"  Validation details: {validation_results}", flush=True)

                                # Log failed validation
                                log_deletion(
                                    file_info={
                                        'file_id': file_id,
                                        'file_name': file_name,
                                        'original_name': file_name,
                                        'json_path': latest_json
                                    },
                                    validation_results=validation_results,
                                    deleted=False,
                                    error="Validation failed"
                                )

                        else:
                            print(f"[Delete] Skipped: No structured JSON files found", flush=True)

                    except Exception as e:
                        print(f"[Warning] Auto-delete failed: {e}", flush=True)
                        print(f"  Cloud file is preserved", flush=True)
                        import traceback
                        print(f"  Traceback: {traceback.format_exc()}", flush=True)

                    print(f"[✓] Completed: {file_name}", flush=True)

                except Exception as e:
                    print(f"[✗] Error processing {file_name}: {e}", flush=True)
                    continue

        except Timeout:
            # Another thread is already processing this file
            print(f"[Skip] {file_name} is being processed by another thread", flush=True)
            continue


def setup_webhook(service, folder_id, webhook_url):
    """Setup Google Drive webhook notification"""
    # Calculate expiration time (24 hours from now)
    expiration_time = int((datetime.utcnow() + timedelta(hours=CHANNEL_EXPIRATION_HOURS)).timestamp() * 1000)

    # Create watch channel
    body = {
        'id': f'channel-{datetime.utcnow().strftime("%Y%m%d%H%M%S")}',
        'type': 'web_hook',
        'address': webhook_url,
        'expiration': expiration_time
    }

    # Watch for changes
    response = service.changes().watch(
        pageToken=get_start_page_token(service),
        body=body
    ).execute()

    # Save channel info
    with open(CHANNEL_FILE, 'w') as f:
        json.dump(response, f)

    print(f"[Webhook] Registered successfully")
    print(f"  Channel ID: {response.get('id')}")
    print(f"  Resource ID: {response.get('resourceId')}")
    print(f"  Expiration: {datetime.fromtimestamp(expiration_time/1000).strftime('%Y-%m-%d %H:%M:%S')}")

    return response


# FastAPI app
app = FastAPI()


@app.post("/webhook")
async def receive_webhook(request: Request):
    """Receive webhook notifications from Google Drive"""
    headers = dict(request.headers)

    # Google Drive sends notifications with specific headers
    resource_state = headers.get('x-goog-resource-state')
    resource_id = headers.get('x-goog-resource-id')
    channel_id = headers.get('x-goog-channel-id')

    print(f"\n[Webhook] Received notification")
    print(f"  State: {resource_state}")
    print(f"  Resource ID: {resource_id}")
    print(f"  Channel ID: {channel_id}")

    if resource_state == 'sync':
        # Initial sync message, just acknowledge
        print("[Webhook] Sync message received (initial setup)")
        return {"status": "ok"}

    if resource_state in ['change', 'update']:
        # Process changes in background using thread
        print("[Debug] Starting background thread for checking changes...")
        thread = threading.Thread(target=check_for_changes_sync)
        thread.daemon = True
        thread.start()

    return {"status": "ok"}


def check_for_changes_sync():
    """Check for changes and process new files (synchronous version for threading)"""
    try:
        print("[Webhook] Checking for changes...", flush=True)
        print("[Debug] Getting Drive service...", flush=True)
        service = get_drive_service()
        print("[Debug] Got Drive service successfully", flush=True)

        folder_id = get_root_folder_id()
        print(f"[Debug] Folder ID: {folder_id}", flush=True)

        # Process new files
        print("[Debug] Calling process_new_files...", flush=True)
        process_new_files(service, folder_id)
        print("[Debug] process_new_files completed", flush=True)

    except Exception as e:
        print(f"[Error] Exception in check_for_changes: {e}", flush=True)
        import traceback
        traceback.print_exc()


@app.on_event("startup")
async def startup_event():
    """Setup webhook on startup"""
    print("=" * 60)
    print("Google Drive Webhook Server (My Drive Root)")
    print("=" * 60)
    print(f"Monitoring: My Drive root (audio files only)")
    print("Detection method: Real-time Push notifications\n")

    # Clean up old lock files from previous runs
    print("[Startup] Cleaning up stale lock files...")
    cleanup_old_locks()

    # Note: Webhook URL needs to be set manually after ngrok starts
    print("[Info] Webhook setup will be done manually after getting ngrok URL")
    print("[Info] Use /setup endpoint to register webhook")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "running", "service": "Google Drive Webhook Server"}


@app.get("/setup")
async def setup_webhook_endpoint(webhook_url: str):
    """Manual webhook setup endpoint"""
    try:
        service = get_drive_service()
        folder_id = get_root_folder_id()
        response = setup_webhook(service, folder_id, f"{webhook_url}/webhook")
        return {"status": "success", "channel": response}
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
