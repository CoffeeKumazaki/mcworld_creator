"""Configurable world height for the anvil writer.

Vanilla Minecraft uses Y=-64..319 (24 sections). With an "extended height"
datapack (custom ``minecraft:overworld`` dimension_type) the build height can be
raised. This module holds the current limits so :class:`EmptyChunk` /
:class:`EmptyRegion` can size their section arrays and validate coordinates
against the active range.

The floor (``WORLD_MIN_Y``) is kept at -64 so the section offset (+4) and the
chunk ``yPos`` (-4) never change -- only the ceiling is raised.

Hard ceiling: Minecraft caps ``min_y + height`` at 2032, so the top block is
Y=2031. That section index (2031 // 16 = 126) is also the highest that fits in
the signed ``TAG_Byte`` used for a section's Y, so 2031 is the absolute maximum.
"""

# Floor is fixed; do not change (keeps section offset +4 and chunk yPos -4 valid)
WORLD_MIN_Y = -64

# Absolute ceiling allowed by Minecraft (min_y + height <= 2032 -> top block 2031)
ABSOLUTE_MAX_Y = 2031

# Vanilla ceiling (used to reset the active state back to default)
VANILLA_MAX_Y = 319

# Active ceiling (vanilla default)
WORLD_MAX_Y = 319

# Number of 16-high sections spanning [WORLD_MIN_Y, WORLD_MAX_Y]
SECTION_COUNT = 24

# Array index of a section = section.y + SECTION_OFFSET (constant while floor is -64)
SECTION_OFFSET = -(WORLD_MIN_Y // 16)  # == 4


def _recompute_sections() -> None:
    global SECTION_COUNT
    SECTION_COUNT = (WORLD_MAX_Y // 16) + 1 - (WORLD_MIN_Y // 16)


def set_world_height(max_y: int) -> None:
    """Raise the active build ceiling to ``max_y`` (inclusive).

    Must be called before constructing any :class:`EmptyRegion`/``EmptyChunk``,
    since the section array is sized at construction time.
    """
    global WORLD_MAX_Y
    if max_y < WORLD_MIN_Y:
        raise ValueError(f"max_y ({max_y}) must be >= WORLD_MIN_Y ({WORLD_MIN_Y})")
    if max_y > ABSOLUTE_MAX_Y:
        raise ValueError(
            f"max_y ({max_y}) exceeds the structural limit {ABSOLUTE_MAX_Y} "
            "(Minecraft dimension cap min_y+height<=2032 and signed section-Y byte)"
        )
    WORLD_MAX_Y = max_y
    _recompute_sections()
