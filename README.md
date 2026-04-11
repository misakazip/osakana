# Osakana

yt-dlp をベースにした GUI ダウンローダー。Windows / Linux (x64・ARM64) 向けのスタンドアロンバイナリを提供します。

## 機能

### ダウンロード
- URL を複数行まとめて入力、またはテキストファイルから一括読み込み
- 動画画質・コンテナ形式の選択
- 音声のみ抽出（mp3 / aac / opus / m4a / flac / wav）
- プレイリスト・チャンネル全体のダウンロード
- aria2c による並列ダウンロード（オプション）
- ダウンロードキュー表示（進捗・速度・残り時間・キャンセル）
- ダウンロード完了時のデスクトップ通知

### 動画処理
- H.265 (HEVC) への再エンコード（ffmpeg 使用）
- 開始・終了時間を指定した切り抜き（トリム）
- トリム用インラインプレビュープレーヤー
- SponsorBlock によるスポンサー区間の自動除去

### 字幕
- 言語・形式（srt / ass / vtt）を指定して埋め込み
- 自動生成字幕の取得（YouTube など）

### 後処理
- サムネイル埋め込み
- メタデータ（タイトル・投稿者・日付など）埋め込み

### ネットワーク
- HTTP/HTTPS/SOCKS プロキシ対応
- ブラウザからのクッキー取得（Chrome / Firefox / Edge / Safari / Brave など）
- bot 検知回避モード（レート制限 + リクエスト間隔）

### その他
- yt-dlp / ffmpeg / aria2c バイナリの自動検出・自動インストール
- yt-dlp 自動アップデート
- ファイル名テンプレート（yt-dlp の `-o` 書式）
- RAW ログ表示
- ダウンロードアーカイブ（重複ダウンロードのスキップ）
- 設定ファイル自動保存（`~/.osakana/config`）
- Catppuccin Mocha ベースのダークテーマ UI

## インストール

### バイナリを使う（推奨）

[Releases](../../releases) ページから OS に合ったバイナリをダウンロードして実行するだけです。追加のインストールは不要です。

| ファイル | 対象 |
|---|---|
| `osakana-windows-x64.exe` | Windows (x64) |
| `osakana-linux-x64` | Linux (x86_64) |
| `osakana-linux-arm64` | Linux (ARM64) |

初回起動時に yt-dlp・ffmpeg が見つからない場合は自動インストールを案内するウィザードが表示されます。

### ソースから実行

**動作要件**

- Python 3.10 以上
- yt-dlp（必須）
- ffmpeg（必須）
- aria2c（オプション）

```bash
git clone https://github.com/misakazip/osakana.git
cd osakana
pip install -r requirements.txt
python src/main.py
```

---

## 使い方

### ダウンロードタブ

1. **URL 欄**に動画 URL を入力（複数行可）、または「ファイルから読み込む」でテキストファイルを選択
2. **フォーマット**で画質・コンテナ・音声形式を選択
3. **オプション**で各種機能を有効化
4. **保存先**フォルダを指定して「ダウンロード」ボタンを押す

### 切り抜き（トリム）

「切り抜き」グループのチェックを入れると展開されます。

- 開始・終了時刻を `HH:MM:SS` または秒数で入力
- 「プレビューを読み込む」で動画をプレビューしながら時刻を確認
- 「← 現在位置」ボタンでプレーヤーの再生位置を時刻欄に反映
- URL 入力から 1.5 秒後に自動でプレビューをロード

### 設定タブ

| セクション | 内容 |
|---|---|
| バイナリパス | yt-dlp / ffmpeg / aria2c のパスを手動指定 |
| ファイル名テンプレート | プリセット選択または yt-dlp 書式で自由入力 |
| ダウンロード制御 | 速度制限・リトライ回数・ダウンロードアーカイブ |
| 字幕 | 言語・形式・自動生成字幕 |
| 後処理 | サムネイル/メタデータ埋め込み・SponsorBlock |
| ネットワーク | プロキシ・クッキー取得元ブラウザ |
| aria2c | 並列ダウンロード設定 |
| yt-dlp アップデート | 手動確認・自動アップデート |

### ファイル名テンプレート

yt-dlp の [OUTPUT TEMPLATE](https://github.com/yt-dlp/yt-dlp#output-template) 書式をそのまま使用できます。

| プレースホルダー | 内容 |
|---|---|
| `%(title)s` | タイトル |
| `%(id)s` | 動画 ID |
| `%(uploader)s` | 投稿者 |
| `%(upload_date)s` | 投稿日 (YYYYMMDD) |
| `%(playlist_index)s` | 再生リスト内番号 |
| `%(ext)s` | 拡張子 |

サブフォルダへの振り分けも可能です。例: `%(uploader)s/%(title)s.%(ext)s`

---

## 設定ファイル

`~/.osakana/config` に `Key: value` 形式で保存されます。

---

## ビルド

GitHub Actions で Windows x64・Linux x64・Linux ARM64 向けのバイナリを自動ビルドします。

```bash
pip install -r requirements.txt pyinstaller
pyinstaller osakana.spec
```

UPX が PATH にある場合は自動で圧縮されます。

---

## ライセンス

本プロジェクト（Osakana）は [GNU General Public License v3.0](LICENSE)（GPL-3.0）の下で公開されています。

依存ライブラリはそれぞれのライセンスに従います。詳細は [LICENSE](LICENSE) ファイルを参照してください。

| ライブラリ | ライセンス |
|---|---|
| PyQt6 | GPL-3.0 |
| Qt 6 | LGPL-3.0 / GPL-3.0 |
| yt-dlp | Unlicense |
| FFmpeg | LGPL-2.1+ (一部 GPL-2.0+) |
| aria2 | GPL-2.0 |
| requests | Apache-2.0 |
