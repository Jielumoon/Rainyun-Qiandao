"""兼容入口：请改用 python -m rainyun，后续会移除。"""

from rainyun.main import run as _run


def run() -> None:
    """兼容入口。"""
    _run()


if __name__ == "__main__":
    run()
