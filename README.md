# endoIsFree

## バージョン

v1.0.0（開発中）

## 使い方

### 設定ファイルの作成

1. `endoCustom/customizer.html` をブラウザーで開きます。
2. 画面の案内に沿って利用者情報、公園・施設、利用日、開始時間を入力します。
3. ダウンロードした `endoCustom.json` をプロジェクト内の `endoCustom/` フォルダーに移動します。

利用者情報は `利用者番号,パスワード` の形式で1行に1件入力します。設定ファイルにはパスワードが含まれます。`endoCustom/` の中に保管し、他人に共有しないでください。このHTMLは入力内容をネットワークへ送信しません。

設定ファイルの読み込み機能は、申し込み処理への統合時に実装します。

### 初回セットアップ

- macOS / Linux:
  1. `python3 -m pip install -r requirements.txt`
  2. `python3 -m playwright install chromium`
- Windows:
  1. `py -3 -m pip install -r requirements.txt`
  2. `py -3 -m playwright install chromium`

### 実行

- macOS / Linux: `./freeEndo.sh`
- Windows: `freeEndo.bat`

どちらもスクリプト自身のあるディレクトリから `main.py` を実行します。実行ログは `logs/endoIsFree.log` に記録されます。
