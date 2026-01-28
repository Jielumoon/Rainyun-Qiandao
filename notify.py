"""兼容层：保留旧的 notify 导入路径。"""

from rainyun.notify import configure, send

__all__ = ["configure", "send"]
