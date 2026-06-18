# model2minecraft

3Dモデル（`.obj` / `.stl` / `.ply` / `.glb` など）を Minecraft のワールド（`.mca` リージョンファイル）に変換するパイプライン。小惑星の形状モデルなどを対象に、2つのモードを持つ。

- **solid** … モデルの**形そのもの**を 1ブロック=1m でボクセル化（中身を詰めたソリッド、または殻）。
- **terrain** … モデル表面を「**中心からの距離（半径）＝高さ**」として等距円筒ハイトマップに展開し、地形カラムを積む。重力方向が常に下になり、**普通に歩ける地形**になる。

内部的に `plateau2minecraft` の voxelize / anvil（.mca書き出し）と、`dem2minecraft` の地形カラム生成パターンを再利用している。

## 実行方法

GDAL 等の依存のため Docker 上での実行を前提とする（リポジトリ直下で）:

```bash
./run_docker.sh          # コンテナに入る
# コンテナ内で:
python model2minecraft --target <model> --output <dir> [options]
```

出力は `<output>/world_data/region/r.{rx}.{rz}.mca` に書き出される。`world_data` をそのまま Minecraft のワールドセーブとして読み込める。

## 共通オプション

| オプション | 既定 | 説明 |
|---|---|---|
| `--target` | （必須） | 入力3Dモデルファイル。`solid` は複数指定可、`terrain` は先頭1つを使用 |
| `--output` | （必須） | 出力フォルダ |
| `--mode` | `solid` | `solid` または `terrain` |
| `--up-axis` | `y` | モデルの上方向軸。`y`（.obj/.glb で一般的）/ `z`。terrain では球面展開の極軸になる |

> モデルの上方向が分からない場合は両方試す。今回の小惑星モデル（リュウグウ/イトカワ）は `--up-axis z`。

## solid モード（形そのもの）

| オプション | 既定 | 説明 |
|---|---|---|
| `--target-size` | `256` | 最長辺をこのブロック数に自動スケール |
| `--block` | `minecraft:stone` | ボクセルに使うブロック |
| `--base-y` | `128` | 配置する垂直中心Y（既定は高さ範囲 `[-64,319]` の中央） |
| `--hollow` | （無し=ソリッド） | 指定すると中身を詰めず**殻だけ**にする |

例:

```bash
# 球（テスト）
python model2minecraft --target asteroid.obj --output data/output/sphere --target-size 128

# 小惑星リュウグウ
python model2minecraft --target data/model/SHAPE_SFM_3M_v20180804.obj \
  --output data/output/ryugu --target-size 256 --base-y 128 --up-axis z

# 殻だけ + ブロック指定
python model2minecraft --target asteroid.obj --output data/output/shell \
  --hollow --block minecraft:deepslate
```

### スケールと高さの注意

- 1ブロック=1m。`--target-size` は**最長辺**の長さ（ブロック数）。
- バニラの建築可能高さは **`-64`〜`319` の383ブロック**ぶんだけ。モデルの**縦方向**がこれを超えると範囲外が省略され、警告が出る（件数を表示）。
- 例: イトカワ（最短軸≈244m）は `--target-size 562` で**1:1** がそのまま収まる。リュウグウ（ほぼ球形・最短≈972m）は1:1だと高さ超過で大半が欠落するため、`terrain` モードか縮小スケールを使う。

## terrain モード（地形に展開）

モデル表面を「中心からの半径」のハイトマップに展開し、その起伏を地形にする。レイキャストではなく**表面点を球面ビンに入れて各方向の最大半径**を取る方式（高速）。

| オプション | 既定 | 説明 |
|---|---|---|
| `--width` | `1024` | 地形マップの幅（経度方向ブロック数） |
| `--height` | `width//2` | 地形マップの高さ（緯度方向ブロック数） |
| `--relief` | `200` | 起伏の振幅（ブロック）。半径 min→`floor-y`、max→`floor-y+relief` にストレッチ |
| `--floor-y` | `-50` | 起伏の最下面Y |
| `--surface-block` | `minecraft:gravel` | 地表のブロック（上3層） |
| `--body-block` | `minecraft:deepslate` | 本体（地中）のブロック |
| `--jobs` | CPU数 | 領域並列ビルドのワーカー数 |

地表から下へ **砂利（上3層）→ 深層岩 → 岩盤（最下2層 `-64,-63`）** の順で積まれる。

例:

```bash
# イトカワを地形として展開
python model2minecraft --mode terrain \
  --target data/model/itokawa_f3145728.stl \
  --output data/output/itokawa_terrain \
  --width 1024 --height 512 --relief 200 --floor-y -50 --up-axis z

# 起伏を弱める / 高解像度
python model2minecraft --mode terrain --target data/model/itokawa_f3145728.stl \
  --output data/output/itokawa_terrain --relief 100 --width 2048 --up-axis z
```

### terrain の注意

- `--relief` を大きくすると起伏が強調（スパイク気味）、小さくするとなだらか。
- 等距円筒のため**上下端（極）は引き伸ばし**、経度±180°に継ぎ目方向ができる（空セル補間は周期境界対応済み）。
- `floor-y + relief` が `319` を超える、または `floor-y < -64` の場合はクランプされ警告が出る。

## 出力構造

```
<output>/
  world_data/
    region/
      r.0.0.mca
      r.-1.0.mca
      ...
```

`world_data` フォルダを Minecraft のセーブとして開く（`level.dat` 等が必要な場合は別途用意）。

## 対応モデル形式

`trimesh` が読める形式すべて（`.obj` / `.stl` / `.ply` / `.glb` / `.off` など）。`Scene`（複数メッシュ）は自動的に単一メッシュへ結合される。
