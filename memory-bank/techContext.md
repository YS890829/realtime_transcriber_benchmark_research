# Technical Context (MVP)

## MVP技術スタック（最小構成）

### コア言語
- **Python**: 3.10以上
- **パッケージ管理**: pip + requirements.txt

### MVP必須ライブラリ（3つのみ）
```python
# faster-whisper - ローカル文字起こし
faster-whisper==1.0.0

# google-generativeai - Gemini API要約
google-generativeai==0.4.0

# python-dotenv - 環境変数管理
python-dotenv==1.0.0
```

### MVPで削除したライブラリ
```python
# ❌ watchdog（手動実行）
# ❌ pydub（faster-whisperが音声処理）
# ❌ openai（Whisper API不使用）
# ❌ anthropic（Claude API不使用）
# ❌ loguru（標準loggingで十分）
# ❌ tqdm（不要）
```

## 開発環境

### 必須要件
- **OS**: macOS 14 (Sonoma) 以上
- **CPU**: Intel Mac（Core i5以上推奨）
- **RAM**: 8GB以上（16GB推奨）
- **ストレージ**: 5GB以上の空き容量
- **Python**: 3.10+

### 推奨ツール
- **エディタ**: VSCode、PyCharm
- **仮想環境**: venv または Poetry
- **Git**: バージョン管理

## 外部依存関係

### システムレベル
```bash
# FFmpeg（音声処理用、faster-whisperが内部で使用）
brew install ffmpeg
```

**注意**: faster-whisperはPythonパッケージなので、whisper.cppのような手動ビルドは不要。`pip install faster-whisper`で自動的にCTranslate2がインストールされる。

### macOS権限
- **Full Disk Access**: `~/Library/Group Containers/` へのアクセス
- **通知**: 処理完了通知の送信

### API要件（MVPではGeminiのみ）

#### Google Gemini API
- **APIキー**: [Google AI Studio](https://aistudio.google.com/)から取得
- **料金**: 無料（1日60リクエスト）
- **制限**: トークン数上限あり（MVP範囲では十分）

**MVPで削除**:
- ❌ OpenAI Whisper API（faster-whisperのみ）
- ❌ Anthropic Claude API（Geminiのみ）

## アーキテクチャ制約

### Intel Mac固有の制約
- **Core ML非対応**: Apple Neural Engine (ANE) は利用不可
- **whisper.cpp最適化**: AVX2命令セットのみ（AVX-512なし）
- **処理速度**: Apple Silicon（M1/M2）の約1/3〜1/5

### ファイルシステム制約
- **ボイスメモパス**: `~/Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings/` (macOS Sonoma以降固定)
- **iCloud同期遅延**: ファイルがすぐに利用可能でない場合あり

### ネットワーク制約
- **API依存**: インターネット接続必須（API使用時）
- **レート制限**: API呼び出し頻度制限
- **タイムアウト**: 長時間リクエストの処理

## セキュリティ考慮事項

### APIキー管理
```python
# .env ファイル（Gitには含めない）
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AI...
ANTHROPIC_API_KEY=sk-ant-...
```

### ファイルアクセス権限
- Voice Memosフォルダへの読み取り専用アクセス
- 出力ディレクトリへの書き込み権限

### データプライバシー
- ローカル処理優先でAPI送信を最小化
- API通信はHTTPS暗号化
- ログファイルに機密情報を含めない

## パフォーマンス要件

### MVP処理速度目標（Intel Mac、mediumモデル）
| 音声長 | 処理時間 |
|--------|----------|
| 10分   | ~40秒   |
| 30分   | ~2分    |
| 60分   | ~4分    |

**注**: whisper.cppより約**5倍高速**

### MVPメモリ使用量（mediumモデル、量子化なし）
| 項目 | 使用量 |
|------|--------|
| メモリ | ~3GB |
| RAM推奨 | 8GB+ |

**推奨理由**: デフォルト設定（量子化なし）でバグ修正が容易

### MVPディスク使用量
| 項目 | サイズ |
|------|--------|
| faster-whisper パッケージ | ~100MB |
| medium モデル | ~3GB |
| Python環境 | ~500MB |
| **合計** | **~3.5GB** |

## 開発ワークフロー

### MVPプロジェクト構造（最小構成）
```
voice-memo-transcriber/
├── .env                    # GEMINI_API_KEY
├── .gitignore
├── requirements.txt        # 3つのパッケージ
├── transcribe.py           # メインスクリプト（200-300行）
└── .processed_files.txt    # 処理済みリスト
```

**MVPで削除**:
- ❌ src/ディレクトリ構造（単一ファイル）
- ❌ config/設定管理（.envのみ）
- ❌ tests/（MVP後に追加）
- ❌ utils/（標準ライブラリで十分）

### MVP環境セットアップ（シンプル化）
```bash
# 1. Python仮想環境作成
python3 -m venv venv
source venv/bin/activate

# 2. 依存関係インストール（3つのみ）
pip install -r requirements.txt

# 3. FFmpegインストール
brew install ffmpeg

# 4. 環境変数設定
echo "GEMINI_API_KEY=your_key_here" > .env

# 5. 実行（初回はモデル自動ダウンロード）
python transcribe.py
```

**MVPで削除**:
- ❌ リポジトリクローン（ローカル開発）
- ❌ テスト（MVP後に追加）

## MVP実行方法（シンプル化）

### 起動
```bash
# 手動実行（新規ファイルを処理）
python transcribe.py
```

### ログ出力
```bash
# 標準出力に表示
INFO: 新規ファイル検出: meeting_20251005.m4a
INFO: 文字起こし中...
INFO: 要約生成中...
INFO: ✅ 処理完了: meeting_20251005.m4a
```

**MVPで削除**:
- ❌ デーモンモード（手動実行のみ）
- ❌ ログファイル（標準出力のみ）
- ❌ macOS通知（ログ出力のみ）
- ❌ 処理統計（不要）

## MVPトラブルシューティング

### よくある問題

#### 1. ボイスメモフォルダが見つからない
```bash
# macOS Sonoma以降を確認
sw_vers

# パスを確認
ls ~/Library/Group\ Containers/group.com.apple.VoiceMemos.shared/Recordings/
```

#### 2. Gemini APIエラー
- APIキーを確認: `echo $GEMINI_API_KEY`
- 1日60リクエスト制限を確認

#### 3. メモリ不足
- mediumモデルで8GB RAM必要
- 他のアプリを終了

## MVP後の拡張候補

MVPで不便を感じた場合のみ追加:
- watchdog自動監視
- Whisper API fallback
- バッチ処理最適化
- Web UI
