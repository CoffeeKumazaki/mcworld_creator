"""
グランドキャニオン地層設定

各層は Main/Sub/Accent ブロックとパターンを持つ。
下から上へ積み上げる。
Minecraftブロック名: https://minecraft.wiki/w/Java_Edition_data_values#Blocks
"""

from dataclasses import dataclass, field


@dataclass
class FossilConfig:
    name: str            # 化石名（参照用）
    block: str           # プレースホルダーブロック
    cluster_size: int    # セルサイズ (ブロック数)
    cluster_chance: int  # セルがクラスターになる確率 (per 1000)
    fill_pct: int        # クラスター内の充填率 (per 100)


@dataclass
class LayerConfig:
    name: str
    thickness: int          # Relative thickness weight
    main: list[str]         # Main blocks
    sub: list[str]          # Sub blocks
    accent: list[str]       # Accent blocks
    main_pct: int           # Main percentage (0-100)
    sub_pct: int            # Sub percentage (0-100)
    accent_pct: int         # Accent percentage (0-100)
    pattern: str            # "horizontal_band" | "irregular" | "veins" | "default"
    discontinuous: bool = False
    discontinuous_pct: float = 1.0
    fossils: list[FossilConfig] = field(default_factory=list)


CANYON_LAYERS_CONFIG = [
    LayerConfig(
        name="basement",
        thickness=250,
        main=["granite"],
        sub=["blackstone", "basalt"],
        accent=["granite", "diorite", "calcite"],
        main_pct=100, sub_pct=0, accent_pct=0,
        pattern="veins",
        fossils=[],
    ),
    LayerConfig(
        name="tapeats",
        thickness=60,
        main=["red_sandstone"],
        sub=["brown_terracotta"],
        accent=["smooth_red_sandstone"],
        main_pct=100, sub_pct=0, accent_pct=0,
        pattern="horizontal_band",
        fossils=[
            FossilConfig("三葉虫", "dead_tube_coral_block", 3, 5, 35),
            FossilConfig("アノマロカリス", "dead_brain_coral_block", 2, 2, 30),
            FossilConfig("ハルキゲニア", "dead_bubble_coral_block", 2, 3, 30),
        ],
    ),
    LayerConfig(
        name="bright_angel",
        thickness=104,
        main=["terracotta"],
        sub=["clay"],
        accent=["light_gray_terracotta", "mud", "gravel"],
        main_pct=100, sub_pct=0, accent_pct=0,
        pattern="irregular",
        fossils=[
            FossilConfig("三葉虫", "dead_tube_coral_block", 3, 5, 35),
            FossilConfig("アノマロカリス", "dead_brain_coral_block", 2, 2, 30),
            FossilConfig("ハルキゲニア", "dead_bubble_coral_block", 2, 3, 30),
        ],
    ),
    LayerConfig(
        name="muav",
        thickness=137,
        main=["light_gray_terracotta"],
        sub=["stone"],
        accent=["light_gray_terracotta", "calcite"],
        main_pct=100, sub_pct=0, accent_pct=0,
        pattern="default",
        fossils=[
            FossilConfig("三葉虫", "dead_tube_coral_block", 3, 5, 35),
            FossilConfig("アノマロカリス", "dead_brain_coral_block", 2, 2, 30),
            FossilConfig("ハルキゲニア", "dead_bubble_coral_block", 2, 3, 30),
        ],
    ),
    LayerConfig(
        name="temple_butte",
        thickness=2,
        main=["yellow_terracotta"],
        sub=["gray_terracotta"],
        accent=["purple_terracotta"],
        main_pct=100, sub_pct=0, accent_pct=0,
        pattern="default",
        discontinuous=True,
        discontinuous_pct=0.30,
        fossils=[],
    ),
    LayerConfig(
        name="redwall",
        thickness=153,
        main=["red_terracotta"],
        sub=["granite", "red_sandstone"],
        accent=["red_terracotta", "red_sandstone"],
        main_pct=100, sub_pct=0, accent_pct=0,
        pattern="default",
        fossils=[
            FossilConfig("プラコダーム", "dead_fire_coral_block", 3, 2, 30),
            FossilConfig("ボスリオレピス", "dead_horn_coral_block", 2, 2, 30),
            FossilConfig("サンゴ", "tube_coral_block", 4, 5, 45),
            FossilConfig("ウミユリ", "horn_coral_block", 3, 4, 40),
        ],
    ),
    LayerConfig(
        name="supai",
        thickness=305,
        main=["orange_terracotta"],
        sub=["orange_terracotta"],
        accent=["brown_terracotta", "smooth_red_sandstone"],
        main_pct=100, sub_pct=0, accent_pct=0,
        pattern="horizontal_band",
        fossils=[
            FossilConfig("オウムガイ", "brain_coral_block", 3, 3, 35),
            FossilConfig("巻貝", "bubble_coral_block", 3, 4, 35),
            FossilConfig("二枚貝", "fire_coral_block", 4, 5, 40),
        ],
    ),
    LayerConfig(
        name="hermit",
        thickness=92,
        main=["brown_terracotta"],
        sub=["red_terracotta"],
        accent=["packed_mud", "terracotta"],
        main_pct=100, sub_pct=0, accent_pct=0,
        pattern="irregular",
        fossils=[
            FossilConfig("メガネウラ", "bone_block", 2, 1, 25),
            FossilConfig("サソリ", "sea_lantern", 2, 2, 25),
            FossilConfig("クモ", "prismarine", 2, 2, 25),
            FossilConfig("エリオプス", "dark_prismarine", 3, 1, 30),
            FossilConfig("ディメトロドン", "prismarine_bricks", 3, 1, 25),
        ],
    ),
    LayerConfig(
        name="coconino",
        thickness=122,
        main=["smooth_sandstone"],
        sub=["smooth_sandstone"],
        accent=["sandstone", "white_terracotta"],
        main_pct=100, sub_pct=0, accent_pct=0,
        pattern="horizontal_band",
        fossils=[
            FossilConfig("メガネウラ", "bone_block", 2, 1, 25),
            FossilConfig("サソリ", "sea_lantern", 2, 2, 25),
            FossilConfig("クモ", "prismarine", 2, 2, 25),
            FossilConfig("エリオプス", "dark_prismarine", 3, 1, 30),
            FossilConfig("ディメトロドン", "prismarine_bricks", 3, 1, 25),
        ],
    ),
    LayerConfig(
        name="toroweap",
        thickness=92,
        main=["sandstone"],
        sub=["light_gray_terracotta"],
        accent=["calcite"],
        main_pct=100, sub_pct=0, accent_pct=0,
        pattern="default",
        fossils=[
            FossilConfig("メガネウラ", "bone_block", 2, 1, 25),
            FossilConfig("サソリ", "sea_lantern", 2, 2, 25),
            FossilConfig("クモ", "prismarine", 2, 2, 25),
            FossilConfig("エリオプス", "dark_prismarine", 3, 1, 30),
            FossilConfig("ディメトロドン", "prismarine_bricks", 3, 1, 25),
        ],
    ),
    LayerConfig(
        name="kaibab",
        thickness=122,
        main=["white_terracotta"],
        sub=["calcite"],
        accent=["diorite", "dirt", "grass_block"],
        main_pct=100, sub_pct=0, accent_pct=0,
        pattern="default",
        fossils=[
            FossilConfig("メガネウラ", "bone_block", 2, 1, 25),
            FossilConfig("サソリ", "sea_lantern", 2, 2, 25),
            FossilConfig("クモ", "prismarine", 2, 2, 25),
            FossilConfig("エリオプス", "dark_prismarine", 3, 1, 30),
            FossilConfig("ディメトロドン", "prismarine_bricks", 3, 1, 25),
        ],
    ),
]
