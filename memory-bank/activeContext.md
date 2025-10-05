# Active Context (MVP)

## 現在のフォーカス

**Phase**: MVP計画フェーズ
**Status**: MVP範囲確定、メモリーバンク更新完了

### 現在の作業
- MVP最小構成への実装プラン変更完了
- メモリーバンク更新完了
- 実装準備完了（transcribe.py作成待ち）

## 最近の変更

### 2025-10-05（初期リサーチ）
- **プロジェクト初期化**: 新規プロジェクトとして開始
- **リサーチ実施**:
  - Clineメモリーバンク構造のベストプラクティス調査
  - iPhoneボイスメモのMac転送方法調査
  - Whisper文字起こし技術（ローカル vs API）比較
  - LLM要約API（Gemini vs Claude）比較
  - macOSボイスメモフォルダ位置とファイル形式調査
  - whisper.cppのIntel Mac対応状況調査

### 2025-10-05（技術選定見直し）
- **追加リサーチ実施**:
  - faster-whisper vs whisper.cpp パフォーマンス比較
  - Whisper large-v3-turbo調査
  - Claude/ChatGPT/Geminiサブスクリプションプランの API アクセス検証
  - ローカLLM（Ollama、Qwen、Llama）調査

### 2025-10-05（MVP範囲確定）
- **MVP検証実施**:
  - 過剰実装の特定（8つの不要機能を削除）
  - 単一スクリプト化（2000行→200-300行）

- **MVP技術選定（最小構成）**:
  - 文字起こし: **faster-whisper**のみ（Whisper API fallback削除）
  - 要約: **Gemini API**のみ（Claude API削除、ローカルLLM削除）
  - ファイル監視: **手動実行**（watchdog削除）
  - 管理: **.processed_files.txt**（DB削除）
  - 言語: Python 3.10+

- **MVPアーキテクチャ**:
  - 単一ファイル（transcribe.py）
  - 4つのシンプルな関数（find_new_files, transcribe_audio, summarize_text, save_output）
  - デザインパターン削除（Strategy Pattern等）

## 次のステップ（MVP）

### 即座に必要なアクション
1. ✅ メモリーバンク更新完了
2. ⬜ transcribe.py実装（200-300行）
3. ⬜ requirements.txt作成
4. ⬜ .env.example作成
5. ⬜ 動作テスト

### MVP実装タスク（シンプル化）
1. **transcribe.py作成**:
   - find_new_files() 関数
   - transcribe_audio() 関数
   - summarize_text() 関数
   - save_output() 関数
   - main() 関数

2. **依存関係**:
   - requirements.txt（3つのみ）
   - .env.example（GEMINI_API_KEY）

3. **動作確認**:
   - 新規ファイル検出テスト
   - 文字起こしテスト
   - 要約テスト
   - 保存テスト

## MVP決定事項

### 確定済み
1. **faster-whisper（量子化なし、mediumモデル）**
   - 決定: デフォルト設定、mediumモデル固定
   - 理由: バグ修正容易、十分高速
   - MVPで削除: モデルサイズ選択、量子化オプション

2. **Gemini APIのみ**
   - 決定: Gemini API（フリーティア）のみ使用
   - 理由: 無料、シンプル
   - MVPで削除: Claude API fallback、ローカルLLM

3. **手動実行**
   - 決定: `python transcribe.py`で手動実行
   - 理由: シンプル
   - MVPで削除: watchdog自動監視、デーモンモード

4. **.processed_files.txt管理**
   - 決定: テキストファイルで処理済み管理
   - 理由: grep可能、シンプル
   - MVPで削除: SQLite、JSON管理

### MVP後に検討
- watchdog自動監視（不便な場合）
- モデルサイズ選択（精度不足の場合）
- バッチ処理最適化（複数ファイル処理の場合）

## MVPリスクと対策

### 技術的リスク
1. **Intel Mac処理速度**
   - リスク: 60分音声→4分処理（許容範囲）
   - 対策: mediumモデルで十分高速

2. **Gemini API制限**
   - リスク: 1日60リクエスト
   - 対策: MVP範囲では十分（1日数件程度）

### MVP後に確認
1. **実機パス確認**
   - macOS Sonoma以降で固定パス検証

2. **処理速度実測**
   - 実機でベンチマーク

3. **無料枠の十分性**
   - 使用頻度によって有料プラン検討

## コンテキストメモ

### ユーザー環境
- **デバイス**: Intel MacBook Pro
- **iPhone**: iPhone 17
- **macOS**: Sonoma (14.x) 以降
- **iCloud**: 有効（ボイスメモ同期）

### プロジェクト背景
- 前プロジェクト: リアルタイム文字起こしiOSアプリ（`realtime_hybrid_transcriber/`）
- 今回: iPhoneで録音→Mac処理のバッチシステム
- 違い: リアルタイムではなく、録音後の処理

### 開発スタイル
- 段階的コミット推奨
- 手動作業の自動化を優先
- メモリーバンクで進捗管理

## 技術的メモ

### MVPセットアップ（最小構成）
```bash
# 1. 仮想環境
python3 -m venv venv
source venv/bin/activate

# 2. 依存関係（3つのみ）
pip install faster-whisper google-generativeai python-dotenv

# 3. FFmpeg
brew install ffmpeg

# 4. 環境変数
echo "GEMINI_API_KEY=your_key" > .env

# 5. 実行
python transcribe.py
```

### transcribe.py概要
```python
from pathlib import Path
from faster_whisper import WhisperModel
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

def find_new_files():
    # 新規ファイル検出
    pass

def transcribe_audio(audio_path):
    model = WhisperModel("medium", device="cpu")
    segments, info = model.transcribe(str(audio_path), language="ja", vad_filter=True)
    return " ".join([seg.text for seg in segments])

def summarize_text(transcript):
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel("gemini-1.5-flash")
    # プロンプト実行
    return response.text

def save_output(filename, transcript, summary):
    # TXT + Markdown保存
    pass

if __name__ == "__main__":
    # メイン処理
    pass
```

## MVP知見

### リサーチから得た知見
1. **faster-whisperの圧倒的性能**: Intel CPUでwhisper.cppより5倍高速
2. **量子化不要**: デフォルト設定で十分高速、デバッグ容易
3. **Gemini フリーティア**: 1日60リクエストでMVP範囲では十分
4. **サブスクリプションプランの制限**: APIアクセス不可（全プラン共通）
5. **単一スクリプトの有効性**: 200-300行で完結、メンテナンス容易

### MVPベストプラクティス
1. **シンプルさ優先**: 複雑な設計パターンを避ける
2. **手動実行**: 自動化は必要になってから
3. **デフォルト設定**: 最適化は実測後に
4. **テキストファイル管理**: grep可能で十分
