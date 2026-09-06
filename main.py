"""五言古诗生成系统的本地试用入口。"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
VENV_ROOT = PROJECT_ROOT / ".venv"
VENV_PYTHON = VENV_ROOT / "bin" / "python"


def ensure_project_runtime() -> None:
    """Use the project virtualenv and source tree when run as a plain script."""

    if VENV_PYTHON.is_file() and Path(sys.prefix).resolve() != VENV_ROOT.resolve():
        os.execv(
            str(VENV_PYTHON),
            [str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]],
        )
    src_dir = str(PROJECT_ROOT / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)


ensure_project_runtime()

from poet import generate_poem


def normalize_cli_topic(topic: str) -> str:
    """Remove quote characters users commonly type around an interactive topic."""

    topic = topic.strip()
    quote_pairs = {'"': '"', "'": "'", "“": "”", "‘": "’"}
    if len(topic) >= 2 and topic[0] in quote_pairs and topic[-1] == quote_pairs[topic[0]]:
        return topic[1:-1].strip()
    return topic


def print_poem(topic: str) -> None:
    result = generate_poem(normalize_cli_topic(topic))
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    # 支持：python main.py "月色"
    if len(sys.argv) > 1:
        print_poem(normalize_cli_topic(" ".join(sys.argv[1:])))
        return

    # 不带参数时进入交互模式，可连续生成多首诗。
    print("五言古诗生成系统")
    print("输入主题后按回车生成；输入 q 或 quit 退出。")
    while True:
        try:
            topic = normalize_cli_topic(input("\n主题> "))
        except (EOFError, KeyboardInterrupt):
            print("\n已退出")
            return

        if topic.casefold() in {"q", "quit", "exit"}:
            print("已退出")
            return
        print_poem(topic)


if __name__ == "__main__":
    main()
