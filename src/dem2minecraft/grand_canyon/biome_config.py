"""
グランドキャニオン地層設定

(ブロック名, 厚さ(ブロック数)) のリスト。下から上へ積み上げる。
層の追加・削除・並び替え・厚さ変更は自由。
Minecraftブロック名: https://minecraft.wiki/w/Java_Edition_data_values#Blocks
"""

CANYON_LAYERS_CONFIG = [
    ("deepslate",           20),   # Vishnu Basement Rocks (最深部)
    ("stone",               15),   # Inner Gorge
    ("terracotta",          20),   # Tapeats Sandstone
    ("red_terracotta",      25),   # Bright Angel Shale
    ("brown_terracotta",    30),   # Muav Limestone
    ("orange_terracotta",   25),   # Redwall Limestone
    ("yellow_terracotta",   30),   # Supai Group
    ("white_terracotta",    20),   # Hermit Shale
    ("sandstone",           30),   # Coconino Sandstone
    ("smooth_sandstone",    25),   # Toroweap Formation
    ("red_sandstone",       30),   # Kaibab Limestone (最上部)
]
