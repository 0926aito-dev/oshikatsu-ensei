# oshikatsu-ensei

推し活の遠征(ライブやイベントへの旅行)を記録・管理するための小さなコマンドラインツールです。

## できること

- 遠征の予定(イベント名・日付・場所・予算)を追加する
- 登録した遠征の一覧を表示する
- 遠征予算の合計を計算する

## 使い方

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

推し活を計画的に楽しむための第一歩として、まずはこの小さなツールから始めまず。
