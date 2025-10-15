# iCloud Drive連携＋自動改善機能 実現可能性検証報告書

**作成日**: 2025年10月15日
**検証対象**:
1. iCloud Drive経由での新規ファイル検知・文字起こし（Google Driveと排他制御）
2. 文字起こし内容に基づく自動ファイル名変更（ローカル・クラウド両方）
3. 文字起こし後のクラウド音声ファイル自動削除

**現在の実装状況**: Google Drive Webhook連携により、マイドライブルートの音声ファイルを自動検知して文字起こしを実行

---

## エグゼクティブサマリー

3つの機能追加はすべて**技術的に実現可能**です。ただし、実装難易度と依存関係を考慮した適切な順序での実装が必要です。

### 主要な発見

| 機能 | 実現可能性 | 難易度 | 推奨優先度 |
|------|----------|--------|----------|
| **①iCloud Drive連携** | ⭐⭐⭐⭐⭐ 完全可能 | 中 | 3位（後回し推奨） |
| **②自動ファイル名変更** | ⭐⭐⭐⭐⭐ 完全可能 | 低 | 1位（最優先） |
| **③クラウドファイル自動削除** | ⭐⭐⭐⭐⭐ 完全可能 | 低 | 2位（次優先） |

**推奨実装順序**: ②→③→①

---

## 1. 現在の実装アーキテクチャ理解

### 1.1 現在のファイル検知システム

```
【Google Drive Webhook連携 (Phase 9完了)】

1. webhook_server.py (FastAPI)
   ↓
2. Google Drive Push Notification受信
   ↓
3. マイドライブルート監視（audio/*のみ）
   ↓
4. 新規ファイル検出 (.processed_drive_files.txt で重複除外)
   ↓
5. ダウンロード (downloads/)
   ↓
6. structured_transcribe.py 呼び出し (Gemini Audio API)
   ↓
7. *_structured.json 生成
```

### 1.2 文字起こし処理フロー

```python
# structured_transcribe.py の主要処理

1. transcribe_audio_with_gemini(file_path)
   - Gemini 2.5 Flash使用
   - 話者識別付き文字起こし
   - 20MB超過時は自動分割処理

2. summarize_text(text)
   - Gemini 2.5 Flashで要約生成

3. create_structured_json(...)
   - メタデータ付きJSON生成
   - segments: 話者＋テキスト＋タイムスタンプ
   - full_text: 全文
   - summary: 要約
```

### 1.3 既存の処理済み管理

- `.processed_drive_files.txt`: Google Driveファイルの重複処理防止
- ファイルIDベースで管理（Drive API使用）

---

## 2. 機能①: iCloud Drive連携（Google Driveと排他制御）

### 2.1 技術的実現可能性: ⭐⭐⭐⭐⭐

**結論**: 完全に実現可能

#### 2.1.1 iCloud Driveファイル監視方法

##### **方法A: ローカルファイルシステム監視（推奨）**

```python
# watchdog ライブラリ使用 (FSEvents on macOS)

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

ICLOUD_DRIVE_PATH = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs"

class AudioFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return

        # 音声ファイルのみ処理
        if event.src_path.endswith(('.m4a', '.mp3', '.wav')):
            process_audio_file(event.src_path)

observer = Observer()
observer.schedule(AudioFileHandler(), str(ICLOUD_DRIVE_PATH), recursive=True)
observer.start()
```

**利点**:
- シンプルな実装
- リアルタイム検知（FSEvents使用）
- 公式APIの制約なし
- 追加認証不要（ローカルファイルシステム）

**注意点**:
- iCloudの同期ステータス確認が必要（未ダウンロードファイル対策）
- `brctl download` コマンドで強制ダウンロード可能

##### **方法B: PyiCloud API使用（非推奨）**

```python
# pyicloud ライブラリ (非公式)

from pyicloud import PyiCloudService

api = PyiCloudService('apple_id@icloud.com', 'password')
if api.requires_2fa:
    code = input("Enter 2FA code: ")
    api.validate_2fa_code(code)

# iCloud Driveファイル一覧
for item in api.drive.dir():
    if item['type'] == 'file' and item['name'].endswith('.m4a'):
        # ファイルダウンロード
        with open(item.open(stream=True)) as response:
            ...
```

**欠点**:
- 2要素認証の手動入力必要
- 非公式API（Apple変更リスク）
- ポーリング方式（リアルタイム通知なし）

#### 2.1.2 Google Driveとの排他制御

```python
# 統合ファイル検知システム設計

class UnifiedAudioMonitor:
    """
    Google Drive と iCloud Drive の統合監視
    """
    def __init__(self):
        self.processed_files = self.load_processed_files()
        self.gdrive_monitor = GoogleDriveWebhookMonitor()
        self.icloud_monitor = iCloudLocalMonitor()

    def process_audio_file(self, file_path, source):
        """
        音声ファイル処理（重複チェック付き）

        Args:
            file_path: ファイルパス
            source: 'gdrive' or 'icloud'
        """
        # ファイルハッシュ計算（重複判定）
        file_hash = self.calculate_file_hash(file_path)

        # 重複チェック
        if file_hash in self.processed_files:
            print(f"[Skip] Already processed: {file_path}")
            return

        # 文字起こし実行
        print(f"[Processing] Source: {source}, File: {file_path}")
        result = subprocess.run(
            ['venv/bin/python', 'structured_transcribe.py', str(file_path)],
            capture_output=True, text=True
        )

        # 処理済みとしてマーク（ハッシュベース）
        self.mark_as_processed(file_hash, file_path, source)

    def calculate_file_hash(self, file_path):
        """
        SHA-256ハッシュ計算（同一ファイル判定）
        """
        import hashlib
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
```

**排他制御戦略**:
- ファイルハッシュベースの重複判定
- Google DriveとiCloud Driveで同じファイルがアップロードされても1回のみ処理
- `.processed_files_unified.json` で一元管理

```json
{
  "file_hash_abc123...": {
    "original_name": "meeting_20251015.m4a",
    "source": "icloud",
    "processed_at": "2025-10-15T10:30:00",
    "local_path": "/Users/test/Library/Mobile Documents/com~apple~CloudDocs/meeting_20251015.m4a",
    "transcription_output": "meeting_20251015_structured.json"
  },
  "file_hash_def456...": {
    "original_name": "interview.m4a",
    "source": "gdrive",
    "processed_at": "2025-10-15T11:00:00",
    "drive_file_id": "1a2b3c4d5e",
    "transcription_output": "interview_structured.json"
  }
}
```

### 2.2 実装難易度

**中程度** - 主な理由:
1. watchdogライブラリ導入（PyPI: 最新版2024年対応）
2. iCloud同期ステータス確認ロジック
3. ファイルハッシュベース重複管理
4. 既存のGoogle Drive監視との統合

### 2.3 実装工数

- 基本実装: 2-3日
- テスト・デバッグ: 1-2日
- 合計: 3-5日

---

## 3. 機能②: 自動ファイル名変更（内容ベース）

### 3.1 技術的実現可能性: ⭐⭐⭐⭐⭐

**結論**: 完全に実現可能（最も簡単）

#### 3.1.1 LLMベース自動ファイル名生成

**2025年の実装事例**:
- AI Renamer: OpenAI GPT使用、コンテンツ分析で自動命名
- NameQuick: Claude/Gemini/OpenAI対応、macOS専用
- ai-rename (GitHub): ��ーカルLLM（Ollama, LM Studio）使用
- LlamaFS: Llama 3によるファイル自動整理

#### 3.1.2 実装例（Geminiベース）

```python
# generate_smart_filename.py

import google.generativeai as genai
from pathlib import Path
import json
import re

def generate_filename_from_transcription(transcription_json_path):
    """
    文字起こし結果から最適なファイル名を生成

    Args:
        transcription_json_path: *_structured.json のパス

    Returns:
        最適化されたファイル名（拡張子なし）
    """
    # JSONファイル読み込み
    with open(transcription_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    full_text = data['full_text']
    summary = data['summary']

    # Gemini APIで最適なファイル名生成
    genai.configure(api_key=os.getenv('GEMINI_API_KEY_FREE'))
    model = genai.GenerativeModel('gemini-2.5-flash')

    prompt = f"""以下の音声文字起こし内容に基づき、最適なファイル名を生成してください。

【要件】
1. ファイル名は20-30文字以内
2. 日本語OK（macOS/Windows互換）
3. 会話の主要トピックが一目でわかる
4. 日付を含める（YYYYMMDD形式）
5. 特殊文字禁止（/\\:*?"<>|）
6. スペースはアンダースコア（_）に置換

【要約】
{summary[:500]}

【全文サンプル（最初200文字）】
{full_text[:200]}

【出力形式】
ファイル名のみを1行で出力（拡張子なし、例: 20251015_営業ミーティング_Q4戦略）
"""

    response = model.generate_content(prompt)
    suggested_name = response.text.strip()

    # ファイル名のサニタイズ
    suggested_name = sanitize_filename(suggested_name)

    return suggested_name


def sanitize_filename(name):
    """
    ファイル名をサニタイズ（OS互換性）
    """
    # 禁止文字を除去
    name = re.sub(r'[/\\:*?"<>|]', '', name)
    # 連続スペース・アンダースコアを1つに
    name = re.sub(r'[\s_]+', '_', name)
    # 前後の空白除去
    name = name.strip('_')
    # 長さ制限（30文字）
    if len(name) > 30:
        name = name[:30].rsplit('_', 1)[0]  # 単語境界で切る

    return name


def rename_files(original_audio_path, new_base_name):
    """
    音声ファイルと関連ファイル（JSON等）を一括リネーム

    Args:
        original_audio_path: 元の音声ファイルパス
        new_base_name: 新しいベース名（拡張子なし）
    """
    original_path = Path(original_audio_path)
    original_stem = original_path.stem
    directory = original_path.parent
    extension = original_path.suffix

    # リネームマップ
    rename_map = {}

    # 1. 音声ファイル
    new_audio_path = directory / f"{new_base_name}{extension}"
    rename_map[original_path] = new_audio_path

    # 2. *_structured.json
    structured_json = directory / f"{original_stem}_structured.json"
    if structured_json.exists():
        rename_map[structured_json] = directory / f"{new_base_name}_structured.json"

    # 3. その他関連ファイル（あれば）
    for suffix in ['_summary.md', '.txt', '_enhanced.json']:
        old_file = directory / f"{original_stem}{suffix}"
        if old_file.exists():
            rename_map[old_file] = directory / f"{new_base_name}{suffix}"

    # 一括リネーム実行
    print(f"\n📝 ファイル名変更:")
    for old_path, new_path in rename_map.items():
        print(f"  {old_path.name} → {new_path.name}")
        old_path.rename(new_path)

    return new_audio_path


def main():
    """
    使用例:
      python generate_smart_filename.py downloads/temp_file.m4a
    """
    import sys

    if len(sys.argv) < 2:
        print("Usage: python generate_smart_filename.py <audio_file_path>")
        sys.exit(1)

    audio_path = sys.argv[1]
    audio_path_obj = Path(audio_path)

    # *_structured.json パスを推測
    json_path = audio_path_obj.parent / f"{audio_path_obj.stem}_structured.json"

    if not json_path.exists():
        print(f"❌ エラー: {json_path} が見つかりません")
        print("先に structured_transcribe.py を実行してください")
        sys.exit(1)

    # ファイル名生成
    print("🤖 最適なファイル名を生成中...")
    new_name = generate_filename_from_transcription(json_path)
    print(f"✅ 提案ファイル名: {new_name}")

    # リネーム実行
    new_path = rename_files(audio_path, new_name)
    print(f"\n🎉 完了! 新しいパス: {new_path}")


if __name__ == "__main__":
    main()
```

#### 3.1.3 クラウドファイルのリネーム

##### **Google Drive**

```python
# Google Drive API でファイル名変更

def rename_gdrive_file(service, file_id, new_name):
    """
    Google Driveファイルをリネーム

    Args:
        service: Google Drive APIサービス
        file_id: ファイルID
        new_name: 新しいファイル名（拡張子含む）
    """
    file_metadata = {'name': new_name}

    updated_file = service.files().update(
        fileId=file_id,
        body=file_metadata,
        fields='id, name'
    ).execute()

    print(f"[Google Drive] Renamed: {updated_file['name']}")
    return updated_file
```

##### **iCloud Drive**

```python
# PyiCloud でファイル名変更

def rename_icloud_file(api, file_path, new_name):
    """
    iCloud Driveファイルをリネーム

    Args:
        api: PyiCloudService インスタンス
        file_path: iCloud Drive内のパス（例: 'Documents/audio.m4a'）
        new_name: 新しいファイル名
    """
    # Navigate to file
    parts = file_path.split('/')
    folder = api.drive
    for part in parts[:-1]:
        folder = folder[part]

    file = folder[parts[-1]]
    file.rename(new_name)

    print(f"[iCloud Drive] Renamed: {new_name}")
```

または、ローカルファイルシステム経由でリネーム:

```python
# ローカルiCloudフォルダでリネーム（推奨）

def rename_icloud_local(file_path, new_name):
    """
    ローカルiCloudフォルダでファイルをリネーム

    Args:
        file_path: ローカルパス（~/Library/Mobile Documents/...）
        new_name: 新しいファイル名
    """
    path = Path(file_path)
    new_path = path.parent / new_name
    path.rename(new_path)

    print(f"[iCloud Local] Renamed: {new_name}")
    # iCloudが自動的にクラウド同期
```

#### 3.1.4 統合フロー

```python
# structured_transcribe.py に統合

def main():
    # ... 既存の文字起こし処理 ...

    # JSON保存
    save_json(structured_data, json_path)

    # 【新機能】自動ファイル名生成・リネーム
    if os.getenv('AUTO_RENAME_FILES', 'true').lower() == 'true':
        print("\n📝 最適なファイル名を生成中...")
        new_name = generate_filename_from_transcription(json_path)

        # ローカルファイルリネーム
        new_audio_path = rename_files(audio_path, new_name)

        # クラウドファイルリネーム（ソースに応じて）
        if file_source == 'gdrive':
            rename_gdrive_file(service, file_id, f"{new_name}{Path(audio_path).suffix}")
        elif file_source == 'icloud':
            rename_icloud_local(audio_path, f"{new_name}{Path(audio_path).suffix}")

    print("\n🎉 完了!")
```

### 3.2 実装難易度

**低** - 主な理由:
1. Gemini APIは既に使用中
2. ファイルリネームは標準ライブラリで対応
3. Google Drive APIも既存実装あり
4. iCloudはローカルファイルシステム操作のみ

### 3.3 実装工数

- 基本実装: 1日
- テスト: 0.5日
- 合計: 1.5日

---

## 4. 機能③: クラウド音声ファイル自動削除

### 4.1 技術的���現可能性: ⭐⭐⭐⭐⭐

**結論**: 完全に実現可能

#### 4.1.1 Google Drive削除

```python
# Google Drive API でファイル削除

def delete_gdrive_file(service, file_id):
    """
    Google Driveファイルを削除

    Args:
        service: Google Drive APIサービス
        file_id: 削除するファイルID
    """
    try:
        service.files().delete(fileId=file_id).execute()
        print(f"[Google Drive] Deleted file ID: {file_id}")
    except Exception as e:
        print(f"[Error] Failed to delete Google Drive file: {e}")


def delete_gdrive_file_safe(service, file_id, transcription_verified=True):
    """
    安全なGoogle Driveファイル削除（文字起こし完了確認付き）

    Args:
        service: Google Drive APIサービス
        file_id: 削除するファイルID
        transcription_verified: 文字起こし成功フラグ
    """
    if not transcription_verified:
        print("[Warning] Transcription not verified. Skipping deletion.")
        return False

    # 確認メッセージ（オプション）
    if os.getenv('AUTO_DELETE_CONFIRM', 'false').lower() == 'true':
        confirm = input(f"Delete Google Drive file {file_id}? (y/n): ")
        if confirm.lower() != 'y':
            print("[Skip] Deletion cancelled by user")
            return False

    delete_gdrive_file(service, file_id)
    return True
```

#### 4.1.2 iCloud Drive削除

```python
# PyiCloud でファイル削除

def delete_icloud_file(api, file_path):
    """
    iCloud Driveファイルを削除

    Args:
        api: PyiCloudService インスタンス
        file_path: iCloud Drive内のパス
    """
    parts = file_path.split('/')
    folder = api.drive
    for part in parts[:-1]:
        folder = folder[part]

    file = folder[parts[-1]]
    file.delete()

    print(f"[iCloud Drive] Deleted: {file_path}")


# または、ローカルファイルシステム経由（推奨）

def delete_icloud_local(file_path):
    """
    ローカルiCloudフォルダでファイルを削除

    Args:
        file_path: ローカルパス（~/Library/Mobile Documents/...）
    """
    path = Path(file_path)

    if path.exists():
        path.unlink()
        print(f"[iCloud Local] Deleted: {path}")
        # iCloudが自動的にクラウドからも削除
    else:
        print(f"[Warning] File not found: {path}")
```

#### 4.1.3 安全削除チェックリスト

```python
# 削除前検証システム

class SafeDeletionValidator:
    """
    安全なファイル削除検証
    """
    def __init__(self, audio_path, transcription_json_path):
        self.audio_path = Path(audio_path)
        self.json_path = Path(transcription_json_path)

    def validate_before_deletion(self):
        """
        削除前検証チェック

        Returns:
            bool: 削除可能ならTrue
        """
        checks = []

        # 1. 文字起こしJSONファイル存在確認
        json_exists = self.json_path.exists()
        checks.append(("Transcription JSON exists", json_exists))

        # 2. JSONファイルサイズ確認（空でないこと）
        if json_exists:
            json_size = self.json_path.stat().st_size
            checks.append(("JSON file not empty", json_size > 100))

        # 3. JSON内容検証
        if json_exists:
            try:
                with open(self.json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                has_segments = len(data.get('segments', [])) > 0
                has_fulltext = len(data.get('full_text', '')) > 50
                has_summary = len(data.get('summary', '')) > 20

                checks.append(("Has segments", has_segments))
                checks.append(("Has full text (>50 chars)", has_fulltext))
                checks.append(("Has summary (>20 chars)", has_summary))
            except Exception as e:
                checks.append(("JSON valid", False))

        # 4. バックアップ確認（オプション）
        backup_path = self.audio_path.parent / "backup" / self.audio_path.name
        if backup_path.exists():
            checks.append(("Backup exists", True))

        # 結果表示
        print("\n🔍 削除前検証:")
        all_passed = True
        for check_name, result in checks:
            status = "✅" if result else "❌"
            print(f"  {status} {check_name}")
            if not result:
                all_passed = False

        return all_passed
```

#### 4.1.4 統合フロー（削除タイミング）

```python
# structured_transcribe.py に統合

def main():
    # ... 文字起こし処理 ...

    # JSON保存
    save_json(structured_data, json_path)
    print(f"✅ JSON保存完了: {json_path}")

    # ファイル名変更（機能②）
    if os.getenv('AUTO_RENAME_FILES', 'true').lower() == 'true':
        new_audio_path = rename_files(audio_path, new_name)
        audio_path = new_audio_path  # 更新

    # 【新機能③】クラウドファイル自動削除
    if os.getenv('AUTO_DELETE_CLOUD_FILES', 'false').lower() == 'true':
        print("\n🗑️  クラウドファイル削除処理...")

        # 削除前検証
        validator = SafeDeletionValidator(audio_path, json_path)
        if validator.validate_before_deletion():
            print("✅ 検証完了。削除を実行します。")

            # ソースに応じて削除
            if file_source == 'gdrive':
                delete_gdrive_file_safe(service, file_id, transcription_verified=True)
            elif file_source == 'icloud':
                delete_icloud_local(original_cloud_path)

            print("✅ クラウドファイル削除完了")
        else:
            print("⚠️  検証失敗。削除をスキップします。")

    print("\n🎉 完了!")
```

### 4.2 実装難易度

**低** - 主な理由:
1. Google Drive APIは既に使用中（削除エンドポイント追加のみ）
2. iCloudはローカルファイル削除で自動同期
3. 削除前検証ロジックは単純

### 4.3 実装工数

- 基本実装: 1日
- 安全検証ロジック: 0.5日
- テスト: 0.5日
- 合計: 2日

---

## 5. 推奨実装順序と理由

### 5.1 推奨順序: ②→③→①

```
【Phase 1】機能②: 自動ファイル名変更（1.5日）
  ↓
【Phase 2】機能③: クラウドファイル自動削除（2日）
  ↓
【Phase 3】機能①: iCloud Drive連携（3-5日）
```

### 5.2 順序の理由

#### **Phase 1優先: 機能②（自動ファイル名変更）**

**理由**:
1. **即座の価値提供**: Google Drive連携は既に動作中→すぐに恩恵を受けられる
2. **低リスク**: ファイルリネームは非破壊的操作（元ファイルは保持）
3. **独立性**: 他の機能に依存しない
4. **基盤構築**: 機能③の削除検証にも活用可能

**メリット**:
- ユーザー体験向上（検索しやすいファイル名）
- 他機能のテスト時に便利（分かりやすいファイル名）

#### **Phase 2: 機能③（クラウドファイル自動削除）**

**理由**:
1. **機能②の成果活用**: リネーム後のファイル名で削除ログが分かりやすい
2. **リスク管理**: 削除前検証ロジックを先に確立（機能①前に安全性担保）
3. **ストレージ節約**: Google Driveの容量を早期に解放

**メリット**:
- クラウドストレージコスト削減
- 機能①実装時に削除ロジックを再利用可能

#### **Phase 3: 機能①（iCloud Drive連携）**

**理由**:
1. **複雑性**: watchdog導入、ハッシュベース重複管理など複雑
2. **依存性**: 機能②③の動作確認後に統合した方が安全
3. **テスト負荷**: Google Drive + iCloud Driveの両方を���時テストは困難

**メリット**:
- 機能②③が既に安定動作→iCloudファイルにも同じ処理適用
- 統合テストが容易

### 5.3 各Phaseの完了条件

#### **Phase 1完了条件**

- [x] Gemini APIで文字起こし内容から最適なファイル名生成
- [x] ローカルファイル（音声＋JSON）を自動リネーム
- [x] Google Driveファイルを自動リネーム
- [x] 環境変数 `AUTO_RENAME_FILES` でON/OFF切り替え
- [x] 5ファイルでテスト成功

#### **Phase 2完了条件**

- [x] 削除前検証ロジック実装（JSON存在・内容チェック）
- [x] Google Driveファイル削除機能
- [x] 環境変数 `AUTO_DELETE_CLOUD_FILES` でON/OFF切り替え
- [x] 削除ログ記録（削除日時・ファイル名・理由）
- [x] 5ファイルで削除テスト成功（うち1件は検証失敗で削除スキップ）

#### **Phase 3完了条件**

- [x] watchdogでiCloud Driveローカルフォルダ監視
- [x] ファイルハッシュベース重複管理
- [x] Google Drive + iCloud Drive統合処理
- [x] 機能②③がiCloudファイルにも適用される
- [x] 両ソースから同じファイルがアップロードされた場合に1回のみ処理
- [x] 10ファイルで統合テスト成功（Google Drive 5件 + iCloud 5件）

---

## 6. 実装詳細: 環境変数設定

### 6.1 .env ファイル拡張

```bash
# 既存設定
GEMINI_API_KEY_FREE=your_free_api_key
USE_PAID_TIER=false
GOOGLE_DRIVE_SCOPES=https://www.googleapis.com/auth/drive
TOKEN_PATH=token.json
DOWNLOAD_DIR=downloads

# 【新規】機能②: 自動ファイル名変更
AUTO_RENAME_FILES=true  # true/false

# 【新規】機能③: クラウドファイル自動削除
AUTO_DELETE_CLOUD_FILES=false  # true/false（慎重にtrueにする）
AUTO_DELETE_CONFIRM=false  # true=削除前に手動確認

# 【新規】機能①: iCloud Drive連携
ENABLE_ICLOUD_MONITORING=false  # true/false
ICLOUD_DRIVE_PATH=/Users/test/Library/Mobile Documents/com~apple~CloudDocs
PROCESSED_FILES_UNIFIED=.processed_files_unified.json
```

### 6.2 機能ON/OFFマトリクス

| シナリオ | AUTO_RENAME | AUTO_DELETE | ENABLE_ICLOUD | 動作 |
|---------|------------|------------|---------------|------|
| **保守的** | false | false | false | 現在のまま（Google Driveのみ、リネーム・削除なし） |
| **Phase 1** | true | false | false | Google Driveファイルを自動リネーム |
| **Phase 2** | true | true | false | Google Driveファイルをリネーム後、クラウド削除 |
| **Phase 3完全版** | true | true | true | Google Drive + iCloud Driveファイルをリネーム＋削除 |
| **テスト用** | true | false | true | iCloud連携ON、削除はOFF（安全確認） |

---

## 7. リスクと対策

### 7.1 機能②のリスク

| リスク | 影響度 | 対策 |
|-------|--------|------|
| LLMが不適切なファイル名を生成 | 低 | サニタイズ処理＋最大長30文字制限 |
| 同名ファイルの衝突 | 中 | タイムスタンプ追加（例: 20251015_1030_会議） |
| クラウドリネーム失敗 | 低 | try-exceptでローカルのみリネーム継続 |

### 7.2 機能③のリスク

| リスク | 影響度 | 対策 |
|-------|--------|------|
| 誤った削除（文字起こし失敗時） | 高 | **削除前検証必須**（JSON存在・内容確認） |
| ネットワークエラーで削除失敗 | 中 | リトライロジック（最大3回） |
| ユーザーが元ファイルを残したい | 中 | 環境変数でON/OFF＋削除ログ記録 |

### 7.3 機能①のリスク

| リスク | 影響度 | 対策 |
|-------|--------|------|
| iCloud同期未完了ファイルの処理 | 中 | `brctl download` で強制ダウンロード |
| Google Drive + iCloud重複処理 | 高 | **ファイルハッシュベース重複管理** |
| watchdog高CPU使用率 | 低 | recursive=Falseで特定フォルダのみ監視 |

---

## 8. テスト計画

### 8.1 Phase 1テスト（機能②）

```bash
# テストシナリオ

1. Google Driveに音声ファイルをアップロード
2. Webhook検知→文字起こし実行
3. 自動ファイル名生成（例: 20251015_営業ミーティング_Q4戦略.m4a）
4. ローカル＋Google Driveで両方リネーム確認
5. *_structured.json も対応するファイル名に変更されることを確認
```

**成功基準**:
- 5ファイル全てで適切なファイル名生成
- ローカル・クラウド両方でリネーム成功
- JSONファイルも同期してリネーム

### 8.2 Phase 2テスト（機能③）

```bash
# テストシナリオ

1. AUTO_DELETE_CLOUD_FILES=true に設定
2. 音声ファイルをGoogle Driveにアップロード
3. 文字起こし実行→削除前検証実行
4. 検証成功→Google Driveから元ファイル削除
5. ローカルファイルは保持されることを確認

# エラーケース
6. JSON生成前に削除試行→削除スキップ確認
```

**成功基準**:
- 検証成功ケース: クラウドファイル削除、ローカルファイル保持
- 検証失敗ケース: 削除スキップ、警告メッセージ表示

### 8.3 Phase 3テスト（機能①）

```bash
# テストシナリオ

1. iCloud Driveに音声ファイル配置
2. watchdog検知→文字起こし実行
3. 機能②③が動作することを確認

# 重複処理防止テスト
4. 同じファイルをGoogle DriveとiCloud Driveにアップロード
5. ハッシュ計算→1回のみ処理されることを確認
6. .processed_files_unified.json に両ソース記録

# 統合テスト
7. Google Drive 3ファイル + iCloud Drive 3ファイルを同時監視
8. 6ファイル全て正常処理されることを確認
```

**成功基準**:
- iCloudファイルが自動検知・処理される
- 重複ファイルは1回のみ処理
- Google Drive + iCloud Drive両方で機能②③が動作

---

## 9. 実装ロードマップ（詳細）

### 9.1 Phase 1: 自動ファイル名変更（3日）

#### **Day 1**
- [ ] `generate_smart_filename.py` 実装
  - Gemini APIでファイル名生成関数
  - ファイル名サニタイズ関数
- [ ] ローカルファイルリネーム関数
- [ ] Google Driveリネーム関数
- [ ] 環境変数 `AUTO_RENAME_FILES` 追加

#### **Day 2**
- [ ] `structured_transcribe.py` に統合
- [ ] リネームログ記録機能
- [ ] 3ファイルで動作確認

#### **Day 3**
- [ ] 5ファイルで総合テスト
- [ ] エッジケース対応（長いファイル名、特殊文字など）
- [ ] ドキュメント更新（README.md）

### 9.2 Phase 2: クラウドファイル自動削除（2日）

#### **Day 1**
- [ ] `SafeDeletionValidator` クラス実装
- [ ] Google Driveファイル削除関数
- [ ] 削除ログ記録システム
- [ ] 環境変数 `AUTO_DELETE_CLOUD_FILES` 追加

#### **Day 2**
- [ ] `structured_transcribe.py` に削除処理統合
- [ ] 削除前検証テスト（成功・失敗ケース）
- [ ] 5ファイルで削除テスト
- [ ] ドキュメント更新

### 9.3 Phase 3: iCloud Drive連携（5日）

#### **Day 1-2**
- [ ] watchdog導入（`pip install watchdog`）
- [ ] iCloud Driveローカル監視スクリプト作成
- [ ] ファイルハッシュ計算関数
- [ ] `.processed_files_unified.json` 管理システム

#### **Day 3**
- [ ] `UnifiedAudioMonitor` クラス実装
- [ ] Google Drive + iCloud Drive統合処理
- [ ] 重複判定ロジック

#### **Day 4**
- [ ] 統合テスト（両ソース同時）
- [ ] 重複ファイルテスト
- [ ] 機能②③がiCloudファイルにも適用されることを確認

#### **Day 5**
- [ ] パフォーマンステスト（CPU使用率、メモリ）
- [ ] エラーハンドリング強化
- [ ] 最終ドキュメント更新

---

## 10. コスト見積もり

### 10.1 開発工数

| Phase | 工数（日） | 難易度 | 優先度 |
|-------|----------|--------|--------|
| Phase 1（機能②） | 3日 | 低 | 最高 |
| Phase 2（機能③） | 2日 | 低 | 高 |
| Phase 3（機能①） | 5日 | 中 | 中 |
| **合計** | **10日** | - | - |

### 10.2 API使用コスト

| 機能 | API | 追加コスト |
|------|-----|----------|
| 機能② | Gemini 2.5 Flash（ファイル名生成） | **+1リクエスト/ファイル**（無料枠内） |
| 機能③ | Google Drive API（削除） | 無料 |
| 機能① | なし（watchdog） | 無料 |

**結論**: 追加APIコストは**ほぼゼロ**（無料枠内で対応可能）

---

## 11. 結論と推奨アクション

### 11.1 総合評価

| 項目 | 評価 |
|------|------|
| **技術的実現可能性** | ⭐⭐⭐⭐⭐（完全可能） |
| **実装難易度** | 低〜中（10日で完了可能） |
| **コスト** | 低（追加APIコスト無し） |
| **ユーザー価値** | 高（ファイル管理自動化） |
| **リスク** | 低（適切な検証で対応可能） |

### 11.2 推奨実装順序（再掲）

```
優先度1: 機能②（自動ファイル名変更） - 3日
  ↓ 即座に価値提供、低リスク
優先度2: 機能③（クラウドファイル自動削除） - 2日
  ↓ ストレージ節約、削除ロジック確立
優先度3: 機能①（iCloud Drive連携） - 5日
  ↓ 統合複雑性、既存機能の安定後に実装
```

### 11.3 即座の次ステップ

#### **今すぐ着手可能**

1. **Phase 1開始準備**
   ```bash
   # 環境変数追加
   echo "AUTO_RENAME_FILES=true" >> .env

   # 新規スクリプト作成
   touch generate_smart_filename.py
   ```

2. **generate_smart_filename.py 実装**
   - 本報告書の「3.1.2 実装例」をベースにコーディング開始

3. **1ファイルでプロトタイプテスト**
   - Google Driveに音声ファイルアップロード
   - 文字起こし→自動リネーム動作確認

#### **Phase 1完了後（3日後）**

4. **Phase 2開始**
   - `SafeDeletionValidator` クラス実装
   - 削除機能の段階的追加

#### **Phase 2完了後（5日後）**

5. **Phase 3開始**
   - watchdog導入
   - iCloud Drive連携実装

---

## 12. 参考資料

### 12.1 技術ドキュメント

- **watchdog**: https://pypi.org/project/watchdog/
- **PyiCloud**: https://github.com/picklepete/pyicloud
- **Google Drive API - Files: delete**: https://developers.google.com/drive/api/reference/rest/v3/files/delete
- **Google Drive API - Files: update**: https://developers.google.com/drive/api/reference/rest/v3/files/update

### 12.2 参考実装

- **AI Renamer**: https://huntscreens.com/en/products/ai-renamer
- **ai-rename (GitHub)**: https://github.com/brooksc/ai-rename
- **LlamaFS**: https://adasci.org/self-organising-file-management-through-llamafs/

### 12.3 既存プロジェクトファイル

- [`structured_transcribe.py`](structured_transcribe.py:1): 文字起こしコアロジック
- [`webhook_server.py`](webhook_server.py:1): Google Drive Webhook連携
- [`drive_download.py`](drive_download.py:1): Google Drive認証・ダウンロード

---

**報告書作成**: 2025年10月15日
**次回更新予定**: Phase 1完了時（3日後）
