"""
グランドキャニオン地層設定

各層は Main/Sub/Accent ブロックとパターンを持つ。
下から上へ積み上げる。
Minecraftブロック名: https://minecraft.wiki/w/Java_Edition_data_values#Blocks
"""

from dataclasses import dataclass


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


CANYON_LAYERS_CONFIG = [
    LayerConfig(
        name="basement",
        thickness=20,
        main=["deepslate"],
        sub=["polished_deepslate", "deepslate_bricks"],
        accent=["tuff", "calcite"],
        main_pct=45, sub_pct=40, accent_pct=15,
        pattern="veins",
    ),
    LayerConfig(
        name="tapeats",
        thickness=15,
        main=["sandstone"],
        sub=["smooth_sandstone", "chiseled_sandstone"],
        accent=["cobblestone", "gravel"],
        main_pct=45, sub_pct=35, accent_pct=20,
        pattern="horizontal_band",
    ),
    LayerConfig(
        name="bright_angel",
        thickness=20,
        main=["green_terracotta"],
        sub=["cyan_terracotta", "lime_terracotta"],
        accent=["clay", "mud"],
        main_pct=35, sub_pct=45, accent_pct=20,
        pattern="irregular",
    ),
    LayerConfig(
        name="muav",
        thickness=25,
        main=["tuff"],
        sub=["tuff_bricks", "polished_tuff"],
        accent=["dripstone_block", "calcite"],
        main_pct=40, sub_pct=45, accent_pct=15,
        pattern="default",
    ),
    LayerConfig(
        name="temple_butte",
        thickness=10,
        main=["tuff"],
        sub=["polished_tuff", "cobblestone"],
        accent=["dripstone_block", "mossy_cobblestone"],
        main_pct=50, sub_pct=35, accent_pct=15,
        pattern="default",
        discontinuous=True,
        discontinuous_pct=0.30,
    ),
    LayerConfig(
        name="redwall",
        thickness=30,
        main=["stone"],
        sub=["stone_bricks", "mossy_stone_bricks"],
        accent=["red_terracotta", "terracotta"],
        main_pct=35, sub_pct=50, accent_pct=15,
        pattern="default",
    ),
    LayerConfig(
        name="supai",
        thickness=25,
        main=["red_sandstone"],
        sub=["smooth_red_sandstone", "chiseled_red_sandstone"],
        accent=["orange_terracotta", "brown_terracotta"],
        main_pct=45, sub_pct=40, accent_pct=15,
        pattern="horizontal_band",
    ),
    LayerConfig(
        name="hermit",
        thickness=20,
        main=["red_terracotta"],
        sub=["terracotta", "brown_terracotta"],
        accent=["mud", "packed_mud"],
        main_pct=50, sub_pct=35, accent_pct=15,
        pattern="irregular",
    ),
    LayerConfig(
        name="coconino",
        thickness=30,
        main=["sandstone"],
        sub=["smooth_sandstone", "cut_sandstone"],
        accent=["white_terracotta", "sand"],
        main_pct=60, sub_pct=30, accent_pct=10,
        pattern="horizontal_band",
    ),
    LayerConfig(
        name="toroweap",
        thickness=25,
        main=["smooth_sandstone"],
        sub=["sandstone", "cut_sandstone"],
        accent=["calcite", "dripstone_block"],
        main_pct=60, sub_pct=25, accent_pct=15,
        pattern="default",
    ),
    LayerConfig(
        name="kaibab",
        thickness=30,
        main=["calcite"],
        sub=["smooth_quartz", "diorite"],
        accent=["bone_block", "white_terracotta"],
        main_pct=50, sub_pct=35, accent_pct=15,
        pattern="default",
    ),
]
