# oshikatsu-ensei

推し活の遠征(ライブやイベントへの旅行)を記録・管理するための小さなツールです。
スマホのブラウザからも使えるWeb版と、Pythonから使えるライブラリ版があります。

## できること

- **これから**: 未来の日付で遠征を登録すると「あと◯日」の予定として表示される
- **これまで**: 過去の日付の遠征は記録として表示され、感想メモ・当日のルート(会場入り→物販→本編、のような流れ)・写真を残せる
- 遠征の編集・削除
- これから/これまで、それぞれの予算合計を表示
- **共有**: 閲覧専用の共有リンクを1つ発行できる。リンクを知っている人はログインなしで自分の推し活記録・予定を見られる(いつでも無効化・再発行が可能)

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

## Renderへのデプロイ

このリポジトリには `render.yaml` を用意しているので、Renderの「New +」→「Blueprint」から
このGitHubリポジトリを選ぶだけでデプロイできます。単体のWeb Serviceとして作る場合は以下の設定にしてください。

- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app`

無料プランでは永続ディスクを付けない限り、再起動時に `trips.db` の中身とアップロードした写真(`static/uploads/`)がリセットされる点に注意してください。

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
