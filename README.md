# oshikatsu-ensei

推し活の遠征(ライブやイベントへの旅行)を記録・管理するための小さなツールです。
スマホのブラウザからも使えるWeb版と、Pythonから使えるライブラリ版があります。

## できること

- **これから**: 未来の日付で遠征を登録すると「あと◯日」の予定として表示される
- **これまで**: 過去の日付の遠征は記録として表示され、感想メモ・当日のルート(会場入り→物販→本編、のような流れ)・写真を残せる
- 遠征の編集・削除
- これから/これまで、それぞれの予算合計を表示
- **共有**: 閲覧専用の共有リンクを1つ発行できる。リンクを知っている人はログインなしで自分の推し活記録・予定を見られる(いつでも無効化・再発行が可能)
- **マップ**: これまでの推し活の訪問地を地図上に表示。あわせて、後述のYouTube連携で見つかった「推しが言った場所」も別の色のピンで重ねて表示する
- **推しの場所(YouTube連携)**: 登録したYouTubeチャンネルの最新動画のタイトル・概要欄から地名を自動検出し、実在する場所として地図上のジオコーディングに成功したものだけを自動でマップに登録する。誤検知に気づいた場合は `/mentions` 画面で地名を編集(再ジオコーディング)したり削除したりできる

これから/これまでの振り分けは日付で自動判定されます(今日より前の日付 = これまで、今日以降 = これから)。

## Web版をローカルで動かす

```bash
pip install -r requirements.txt
python app.py
```

ブラウザで `http://127.0.0.1:5000` を開くと、フォームから遠征の追加・編集・削除、共有リンクの発行ができます。
データは `trips.db`(SQLite)、写真は `static/uploads/` に保存されます。

現在は共有リンクは1本のみ(アカウント・フレンド機能はまだありません)。将来的にはアカウント制にして、
特定のフレンドだけに共有できるようにする予定です。

## YouTube連携(推しの場所)を使う

`/channels` 画面からYouTubeチャンネルを登録し、「最新動画をチェックする」を押すと、
最新動画のタイトル・概要欄から地名を自動検出してマップに追加します。使うには
YouTube Data API v3 のAPIキーが必要です。

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成(または既存のものを利用)
2. 「APIとサービス」→「ライブラリ」から **YouTube Data API v3** を有効化
3. 「認証情報」→「認証情報を作成」→「APIキー」でキーを発行
4. 環境変数 `YOUTUBE_API_KEY` にそのキーを設定する
   - ローカル: `export YOUTUBE_API_KEY=xxxx`(PowerShellなら `$env:YOUTUBE_API_KEY = "xxxx"`)してから `python app.py`
   - Render: サービスの Environment タブで `YOUTUBE_API_KEY` を追加

`/channels` 画面には、坂道系グループの主要チャンネルをワンクリックで追加できる「クイック追加」ボタンと、
乃木坂46/櫻坂46/日向坂46の公式サイトのニュース一覧ページへのリンクも用意しています
(ファンクラブ・公式サイトの内容は自動取得していません。手動で確認してください)。

地名の判定には [OpenStreetMap Nominatim](https://nominatim.openstreetmap.org/) の無料ジオコーディングを利用しています。
地図のタイル・ジオコーディングともにAPIキーは不要です。

### 月1回の自動チェック

`/channels/check` を毎月1回自動で呼び出すGitHub Actionsワークフロー(`.github/workflows/monthly-channel-check.yml`)を
用意しています。無料で動作し、Renderの有料プランは不要です(スケジュール実行のタイミングはGitHub側の混雑状況により
多少前後することがあります)。

`/channels/check` は認証なしだと誰でも呼び出せてしまい、YouTube APIのクォータを消費されてしまうため、
環境変数 `CHECK_TOKEN` を設定すると、一致するトークンを持つリクエストだけを受け付けるようになります
(未設定の場合はこれまで通り誰でも呼び出せます)。

自動チェックを有効にする場合:

1. Renderのサービス環境変数に `CHECK_TOKEN` を設定する(値はGitHub Secretsの `CHECK_TOKEN` と同じものにする)
2. GitHubリポジトリの Secrets に同じ値で `CHECK_TOKEN` を登録する(`gh secret set CHECK_TOKEN` など)
3. `/channels` 画面の「最新動画をチェックする」ボタンは、`CHECK_TOKEN` が設定されていれば自動的にトークンを付けて送信するので、手動チェックも引き続き使えます

GitHub Actionsの画面から「Run workflow」を選べば、月初を待たずに手動実行することもできます。

## Renderへのデプロイ

このリポジトリには `render.yaml` を用意しているので、Renderの「New +」→「Blueprint」から
このGitHubリポジトリを選ぶだけでデプロイできます。単体のWeb Serviceとして作る場合は以下の設定にしてください。

- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app`

無料プランでは永続ディスクを付けない限り、再起動時に `trips.db` の中身(登録したチャンネルや推しの場所を含む)と
アップロードした写真(`static/uploads/`)がリセットされる点に注意してください。

## Pythonライブラリとして使う

```python
from trip_manager import TripManager

manager = TripManager()
manager.add_trip("〇〇ライブ", "2026-08-15", "東京", 25000)
manager.add_trip("△△イベント", "2026-09-01", "大阪", 18000)

for trip in manager.list_trips():
    print(trip)

print(manager.total_budget())  # 43000
```

## テストの実行

```bash
pip install -r requirements.txt
pytest
```

推し活を計画的に楽しむための第一歩として、まずはこの小さなツールから始めます。
