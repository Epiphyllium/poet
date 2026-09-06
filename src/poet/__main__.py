"""Command-line demonstration: python -m poet TOPIC."""

from __future__ import annotations

import argparse
import json

from .service import generate_poem


def main() -> None:
    parser = argparse.ArgumentParser(description="生成一首四句五言古诗")
    parser.add_argument("topic", nargs="?", default="月色", help="诗歌主题")
    args = parser.parse_args()
    print(json.dumps(generate_poem(args.topic), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
