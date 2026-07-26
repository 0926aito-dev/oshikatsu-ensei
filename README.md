# oshikatsu-ensei

推し活の遠征(ライブやイベントへの旅行)を記録・管理するための小さなツールです。
スマホのブラウザからも使えるWeb版と、Pythonから使えるライブラリ版があります。

## できること

- 遠征の予定(イベント名・日付・場所・予算)を追加する
- 登録した遠征の一覧を表示する
- 遠征予算の合計を計算する

## Web版をローカルで動かす

```bash
pip install -r requirements.txt
python app.py
```

ブラウザで `http://127.0.0.1:5000` を開くと、フォームから遠征の追加・削除ができます。
データは `trips.db`(SQLite)に保存されます。

## Renderへのデプロイ

このリポジトリには `render.yaml` を用意しているので、Renderの「New +」→「Blueprint」から
このGitHubリポジトリを選ぶだけでデプロイできます。単体のWeb Serviceとして作る場合は以下の設定にしてください。

- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app`

無料プランでは永続ディスクを付けない限り、再起動時に `trips.db` の中身がリセットされる点に注意してください。

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
