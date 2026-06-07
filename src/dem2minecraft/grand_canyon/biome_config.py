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
            FossilConfig("tapeats_fossil", "dead_tube_coral_block", 3, 10, 33),
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
            FossilConfig("bright_angel_fossil", "dead_brain_coral_block", 3, 10, 33),
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
            FossilConfig("muav_fossil", "dead_bubble_coral_block", 3, 10, 33),
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
            FossilConfig("redwall_fossil", "dead_fire_coral_block", 3, 12, 42),
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
            FossilConfig("supai_fossil", "dead_horn_coral_block", 3, 12, 37),
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
            FossilConfig("hermit_fossil", "tube_coral_block", 2, 6, 30),
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
            FossilConfig("coconino_fossil", "brain_coral_block", 2, 6, 30),
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
            FossilConfig("toroweap_fossil", "bubble_coral_block", 2, 6, 30),
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
            FossilConfig("kaibab_fossil", "fire_coral_block", 2, 6, 30),
        ],
    ),
]
