# endoIsFree

## バージョン

v1.0.0（開発中）

## 使い方

### 設定ファイルの作成

1. `endoCustom/customizer.html` をブラウザーで開きます。
2. 画面の案内に沿って利用者情報、公園・施設、利用日、開始時間を入力します。
3. ダウンロードした `endoCustom.json` をプロジェクト内の `endoCustom/` フォルダーに移動します。

利用者情報は `利用者番号,パスワード` の形式で1行に1件入力します。設定ファイルにはパスワードが含まれます。`endoCustom/` の中に保管し、他人に共有しないでください。このHTMLは入力内容をネットワークへ送信しません。

利用者情報はログインに使用します。step4では抽選分類「テニス（人工芝）」を選択し、step5では設定した公園・施設を選択して利用日テーブルの表示を確認します。日付・時間の選択と申し込み確定は後続ステップで対応します。

アプリケーションは設定ファイルの利用者を1件ずつ処理し、各利用者についてstep1からstep7まで順番に実行します。アカウントごとにブラウザーセッションを分けます。

### 初回セットアップ

- Python 3.10以降をインストールしてください。まだ入っていない場合は [Python公式ダウンロードページ](https://www.python.org/downloads/) からインストーラーを取得します。
- Windowsではインストール時に「Add python.exe to PATH」とPython Launcherを有効にしてください。インストール後、コマンドプロンプトで `py -3 --version` を実行して確認します。
- macOS / Linuxではターミナルで `python3 --version` を実行して確認します。

- macOS / Linux:
  1. `python3 -m pip install -r requirements.txt`
  2. `python3 -m playwright install chromium`
- Windows:
  1. `py -3 -m pip install -r requirements.txt`
  2. `py -3 -m playwright install chromium`

### 実行

- macOS / Linux: `./freeEndo.sh`
- Windows: `freeEndo.bat`

どちらもスクリプト自身のあるディレクトリから `main.py` を実行します。実行ログは `logs/endoIsFree.log` に記録されます。更新スクリプトの実行結果は `logs/nightlyUpdate.log` に追記されます。
