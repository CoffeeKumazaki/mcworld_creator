"""
Bedrock ワールド内の化石プレースホルダーブロックをカスタムブロック ID に一括置換する。

Usage:
    python scripts/replace_fossil_blocks.py \
        --world /path/to/bedrock/world \
        --mapping scripts/fossil_block_mapping.json \
        [--dry-run]

依存: amulet-core (uv run --with amulet-core で実行可能)

マッピング JSON は amulet の universal フォーマット上のブロックを対象とする。
各 replacement は `from`（`namespace:base_name`）と任意の `properties`（プロパティ
完全一致条件）を持ち、両方が一致したパレットエントリを置換する。
（Chunker で Bedrock 変換されたサンゴは `universal_minecraft:coral_block` +
 `coral_type`/`dead` プロパティに畳まれるため、プロパティ一致が必須。）
"""

import argparse
import json
import sys
from pathlib import Path

import amulet
from amulet.api.block import Block


def _prop_value(tag) -> str:
    """amulet_nbt のプロパティ値タグを比較用の文字列に正規化する。"""
    if hasattr(tag, "py_data"):
        return str(tag.py_data)
    return str(tag)


def load_mapping(mapping_path: str) -> list[dict]:
    """JSON マッピングを読み込み、ルール（from/properties/to/label）のリストを返す。"""
    with open(mapping_path) as f:
        data = json.load(f)

    namespace = data["namespace"]
    rules: list[dict] = []
    for entry in data["replacements"]:
        from_id = entry["from"]                      # e.g. "universal_minecraft:coral_block"
        props = entry.get("properties", {})          # e.g. {"coral_type": "tube", "dead": "true"}
        to_block = Block(namespace, entry["to"])      # e.g. Block("gc_psl", "tapeats_fossil")
        prop_str = ",".join(f"{k}={v}" for k, v in sorted(props.items()))
        label = f"{from_id}[{prop_str}]" if prop_str else from_id
        rules.append({"from": from_id, "properties": props, "to": to_block, "label": label})

    return rules


def block_matches(block, rule: dict) -> bool:
    """パレットブロックがルールの from/properties をすべて満たすか判定する。"""
    if f"{block.namespace}:{block.base_name}" != rule["from"]:
        return False
    for key, expected in rule["properties"].items():
        if key not in block.properties:
            return False
        if _prop_value(block.properties[key]) != str(expected):
            return False
    return True


def replace_blocks(world_path: str, rules: list[dict], dry_run: bool) -> dict[str, int]:
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

                palette = chunk.block_palette
                # 旧パレット index -> (rule, 新 index) の対応を作る。
                remap: dict[int, tuple[dict, int]] = {}
                for idx in range(len(palette)):
                    block = palette[idx]
                    rule = next((r for r in rules if block_matches(block, r)), None)
                    if rule is None:
                        continue
                    new_idx = idx if dry_run else palette.get_add_block(rule["to"])
                    remap[idx] = (rule, new_idx)

                if not remap:
                    continue

                changed = False
                for cy in chunk.blocks.sub_chunks:
                    arr = chunk.blocks.get_sub_chunk(cy)
                    for old_idx, (rule, new_idx) in remap.items():
                        mask = arr == old_idx
                        n = int(mask.sum())
                        if not n:
                            continue
                        counts[rule["label"]] = counts.get(rule["label"], 0) + n
                        if not dry_run:
                            arr[mask] = new_idx
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

    rules = load_mapping(mapping_path)
    print(f"Loaded {len(rules)} block replacements")
    if args.dry_run:
        print("=== DRY RUN (no changes will be saved) ===")

    counts = replace_blocks(world_path, rules, args.dry_run)

    print("\n--- Summary ---")
    total = 0
    by_label = {r["label"]: r["to"] for r in rules}
    for label, count in sorted(counts.items()):
        target = by_label[label]
        print(f"  {label} -> {target.namespace}:{target.base_name}: {count} blocks")
        total += count
    print(f"  Total: {total} blocks {'(would be replaced)' if args.dry_run else 'replaced'}")


if __name__ == "__main__":
    main()
