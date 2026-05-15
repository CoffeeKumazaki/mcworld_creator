"""
Bedrock ワールド内の化石プレースホルダーブロックをカスタムブロック ID に一括置換する。

Usage:
    python scripts/replace_fossil_blocks.py \
        --world /path/to/bedrock/world \
        --mapping scripts/fossil_block_mapping.json \
        [--dry-run]

依存: amulet-core (uv run --with amulet-core で実行可能)
"""

import argparse
import json
import sys
from pathlib import Path

import amulet
from amulet.api.block import Block


def load_mapping(mapping_path: str) -> dict[str, Block]:
    """JSON マッピングファイルを読み込み、{from_block_str: Block} の辞書を返す。"""
    with open(mapping_path) as f:
        data = json.load(f)

    namespace = data["namespace"]
    mapping = {}
    for entry in data["replacements"]:
        from_id = entry["from"]  # e.g. "minecraft:dead_tube_coral_block"
        to_name = entry["to"]    # e.g. "trilobite"
        to_block = Block(namespace, to_name)
        mapping[from_id] = to_block

    return mapping


def replace_blocks(world_path: str, mapping: dict[str, Block], dry_run: bool) -> dict[str, int]:
    """ワールド内の全チャンクを走査し、パレット置換で化石ブロックを一括変換する。"""
    level = amulet.load_level(world_path)
    counts: dict[str, int] = {}

    try:
        for dim in level.dimensions:
            chunk_coords = list(level.all_chunk_coords(dim))
            print(f"Dimension {dim}: {len(chunk_coords)} chunks")

            for cx, cz in chunk_coords:
                try:
                    chunk = level.get_chunk(cx, cz, dim)
                except Exception:
                    continue

                changed = False
                palette = chunk.block_palette
                for idx in range(len(palette)):
                    block = palette[idx]
                    block_id = f"{block.namespace}:{block.base_name}"

                    if block_id in mapping:
                        new_block = mapping[block_id]
                        # パレット内のブロック数をカウント
                        block_count = int((chunk.blocks == idx).sum())
                        counts[block_id] = counts.get(block_id, 0) + block_count

                        if not dry_run:
                            palette[idx] = new_block
                            changed = True

                if changed:
                    chunk.changed = True

        if not dry_run:
            level.save()
    finally:
        level.close()

    return counts


def main():
    parser = argparse.ArgumentParser(
        description="Bedrock ワールドの化石プレースホルダーブロックをカスタムブロック ID に置換"
    )
    parser.add_argument("--world", required=True, help="Bedrock ワールドのパス")
    parser.add_argument("--mapping", required=True, help="マッピング JSON ファイルのパス")
    parser.add_argument("--dry-run", action="store_true", help="実際に書き換えず置換数のみ表示")
    args = parser.parse_args()

    world_path = args.world
    mapping_path = args.mapping

    if not Path(world_path).is_dir():
        print(f"Error: ワールドが見つかりません: {world_path}", file=sys.stderr)
        sys.exit(1)
    if not Path(mapping_path).is_file():
        print(f"Error: マッピングファイルが見つかりません: {mapping_path}", file=sys.stderr)
        sys.exit(1)

    mapping = load_mapping(mapping_path)
    print(f"Loaded {len(mapping)} block replacements")
    if args.dry_run:
        print("=== DRY RUN (no changes will be saved) ===")

    counts = replace_blocks(world_path, mapping, args.dry_run)

    print("\n--- Summary ---")
    total = 0
    for block_id, count in sorted(counts.items()):
        target = mapping[block_id]
        print(f"  {block_id} -> {target.namespace}:{target.base_name}: {count} blocks")
        total += count
    print(f"  Total: {total} blocks {'(would be replaced)' if args.dry_run else 'replaced'}")


if __name__ == "__main__":
    main()
