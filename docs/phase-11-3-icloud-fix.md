# Phase 11-3 iCloud Drive統合修正

**作成日**: 2025-10-17
**対象**: iCloud Drive経由のファイルでPhase 11-3が実行されない問題の修正

## 問題の概要

### 現象
- Google Drive経由のファイル: Phase 11-3が正常に実行される（10ステップ完了）
- iCloud Drive経由のファイル: Phase 11-3が実行されない（enhanced JSONファイルが生成されない）

### テスト結果

| ファイル | ソース | Phase 11-3実行 | enhanced JSON | Meeting ID |
|---------|--------|--------------|--------------|-----------|
| Shop 114 | Google Drive | ✅ 実行 | ✅ 生成 | 13073fcd-... |
| Shop 117 | iCloud Drive | ❌ 未実行 | ❌ 未生成 | - |
| Shop 119 | iCloud Drive | ❌ 未実行 | ❌ 未生成 | - |

## 根本原因

### 原因1: `.env`ファイルが読み込まれていない

**ファイル**: `src/monitoring/icloud_monitor.py`

**問題点**:
- `dotenv`のインポートがない
- `load_dotenv()`の呼び出しがない
- 環境変数`ENABLE_INTEGRATED_PIPELINE`が読み込まれない

**対比**:
- `webhook_server.py`: ✅ `load_dotenv()`あり
- `icloud_monitor.py`: ❌ `load_dotenv()`なし

### 原因2: サブプロセスに環境変数が渡されていない

**ファイル**: `src/monitoring/icloud_monitor.py`, `src/monitoring/webhook_server.py`

**問題点**:
```python
# 修正前（環境変数が渡されない）
result = subprocess.run(cmd, capture_output=True, text=True)
```

**影響**:
- サブプロセス（`structured_transcribe.py`）が環境変数にアクセスできない
- `os.getenv('ENABLE_INTEGRATED_PIPELINE', 'true')`がデフォルト値'true'ではなく空文字列を返す可能性がある

### 原因3: `.env`に設定が不足

**ファイル**: `.env`

**問題点**:
- `ENABLE_INTEGRATED_PIPELINE`の定義がない
- `ENABLE_VECTOR_DB`の定義がない

## 修正内容

### 修正1: dotenv読み込み追加

**ファイル**: `src/monitoring/icloud_monitor.py`
**行番号**: 24-27

```python
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()
```

### 修正2: サブプロセスへの環境変数引き渡し

**ファイル**: `src/monitoring/icloud_monitor.py`
**行番号**: 340

```python
# 修正後
result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    env=os.environ.copy(),  # 環境変数を継承
    timeout=3600
)
```

**ファイル**: `src/monitoring/webhook_server.py`
**行番号**: 139

```python
# 修正後
result = subprocess.run(cmd, capture_output=True, text=True, env=os.environ.copy())
```

### 修正3: .env設定追加

**ファイル**: `.env`
**行番号**: 50-54

```bash
# Phase 11-3: 統合パイプライン（参加者管理 + エンティティ解決 + 話者推論）
ENABLE_INTEGRATED_PIPELINE=true

# Phase 11-4: Vector DB自動構築
ENABLE_VECTOR_DB=true
```

### 修正4: Phase 11-3ログ表示機能

**ファイル**: `src/monitoring/icloud_monitor.py`
**行番号**: 346-355

```python
# Phase 11-3のログ出力を表示
if "Phase 11-3" in result.stdout:
    print("\n" + "=" * 70, flush=True)
    print("📊 Phase 11-3 実行ログ:", flush=True)
    print("=" * 70, flush=True)
    # Phase 11-3セクションのみ抽出して表示
    for line in result.stdout.split('\n'):
        if 'Phase 11-3' in line or 'Step' in line or 'Meeting ID' in line or '✓' in line or '⏭' in line:
            print(f"  {line}", flush=True)
    print("=" * 70 + "\n", flush=True)
```

## 検証方法

### 1. サービス再起動

```bash
# 既存プロセスを停止して再起動
ps aux | grep -E 'icloud_monitor|webhook_server' | grep -v grep | awk '{print $2}' | xargs kill
./venv/bin/python3 -m src.monitoring.icloud_monitor > icloud_monitor.log 2>&1 &
./venv/bin/python3 -m src.monitoring.webhook_server > webhook_server.log 2>&1 &
```

### 2. iCloud Driveテスト

```bash
# 1. iPhone/iPadでボイスメモを録音
# 2. iCloud同期を待つ（数秒）
# 3. ログを確認
tail -f icloud_monitor.log
```

### 3. 期待される出力

```
============================================================
📊 Phase 11-3 実行ログ:
============================================================
  🔄 Phase 11-3統合パイプライン自動実行
  ⏭  Step 1: JSON読み込み
  ✓ JSON読み込み完了
  ⏭  Step 2: カレンダーマッチング
  ✓ カレンダーマッチング完了
  ⏭  Step 3: 参加者抽出（LLM）
  ✓ 参加者抽出完了: 2名
  ⏭  Step 4: 参加者DB検索
  ✓ 参加者DB検索完了
  ⏭  Step 5: トピック/エンティティ抽出（LLM）
  ✓ トピック/エンティティ抽出完了
  ⏭  Step 6: エンティティ解決
  ✓ エンティティ解決完了
  ⏭  Step 7: 話者推論（LLM）
  ✓ 話者推論完了
  ⏭  Step 8: 要約生成（LLM）
  ✓ 要約生成完了
  ⏭  Step 9: 参加者DB更新
  ✓ 参加者DB更新完了
  ⏭  Step 10: 会議情報登録
  ✓ 会議情報登録完了
  ✅ 統合パイプライン完了
     Meeting ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
     参加者: X名
============================================================
```

### 4. 生成ファイル確認

```bash
# enhanced JSONファイルが生成されることを確認
ls -lh downloads/*_structured_enhanced.json | tail -1
```

## まとめ

### 修正前の処理フロー（iCloud Drive）

```
音声ファイル（iCloud Drive）
  ↓
icloud_monitor.py（環境変数なし）
  ↓
subprocess.run（環境変数が渡されない）
  ↓
structured_transcribe.py（ENABLE_INTEGRATED_PIPELINE読み込めず）
  ↓
Phase 11-3スキップ ❌
  ↓
*_structured.json のみ生成
```

### 修正後の処理フロー（iCloud Drive）

```
音声ファイル（iCloud Drive）
  ↓
icloud_monitor.py（.env読み込み✅）
  ↓
subprocess.run（env=os.environ.copy()で環境変数を渡す✅）
  ↓
structured_transcribe.py（ENABLE_INTEGRATED_PIPELINE=true読み込み✅）
  ↓
Phase 11-3実行（10ステップ完了）✅
  ↓
*_structured_enhanced.json 生成✅
  ↓
Phase 11-4: Vector DB構築✅
```

## 関連ファイル

- [src/monitoring/icloud_monitor.py](../src/monitoring/icloud_monitor.py) - 主要修正ファイル
- [src/monitoring/webhook_server.py](../src/monitoring/webhook_server.py) - 環境変数引き渡し修正
- [.env](../.env) - Phase 11-3/11-4設定追加
- [src/transcription/structured_transcribe.py](../src/transcription/structured_transcribe.py) - Phase 11-3呼び出し元
- [src/pipeline/integrated_pipeline.py](../src/pipeline/integrated_pipeline.py) - Phase 11-3実装

## テスト状況

| 項目 | 実行結果 |
|-----|---------|
| dotenv読み込み | ✅ 実装完了 |
| 環境変数引き渡し | ✅ 実装完了 |
| .env設定追加 | ✅ 実装完了 |
| ログ表示機能 | ✅ 実装完了 |
| サービス再起動 | ✅ 完了（PID: 7211, 7212） |
| End-to-Endテスト | ⏳ ユーザーによるテスト待ち |

## 次のステップ

1. **ユーザーテスト**: 新しいiCloud Drive音声ファイルをアップロードして検証
2. **ログ確認**: `icloud_monitor.log`にPhase 11-3の10ステップが表示されることを確認
3. **enhanced JSON確認**: `downloads/`に`*_structured_enhanced.json`が生成されることを確認
4. **Meeting ID確認**: 会議情報がparticipants.dbに登録されることを確認
