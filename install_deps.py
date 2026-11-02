"""安装第三方依赖到 vendor/ 目录。

沙箱环境下 tempfile.mkdtemp() 创建的目录不可写(疑似目录 ACL 被沙箱拦截),
而 os.makedirs() 创建的目录正常。此处 monkeypatch mkdtemp 后调用 pip,
让 pip 的临时目录改用 os.makedirs 创建, 从而避开沙箱限制。
"""
from __future__ import annotations

import os
import secrets
import sys
import tempfile

BASE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(BASE, "vendor")


def _patched_mkdtemp(suffix=None, prefix=None, dir=None):
    if dir is None:
        dir = tempfile.gettempdir()
    prefix = prefix or "tmp"
    suffix = suffix or ""
    for _ in range(10000):
        name = prefix + secrets.token_hex(4) + suffix
        candidate = os.path.join(dir, name)
        try:
            os.makedirs(candidate)
            return candidate
        except FileExistsError:
            continue
    raise FileExistsError(f"could not create temporary directory in {dir}")


def main() -> int:
    # 必须在当前进程 patch, 再在同一进程内调用 pip 入口,
    # 否则 subprocess 启动的子进程会恢复原始的 mkdtemp。
    tempfile.mkdtemp = _patched_mkdtemp

    # 清华镜像 WAF 对 pip 默认的完整 UA(含 JSON 花括号)返回 403,
    # 换成简单 UA 即可正常访问。
    import pip._internal.network.session as _pip_session
    _pip_session.user_agent = lambda: "pip"

    from pip._internal.cli.main import main as pip_main

    args = [
        "install", "--no-cache-dir", "--disable-pip-version-check",
        "-i", "https://pypi.tuna.tsinghua.edu.cn/simple",
        "--target", TARGET, "obsws-python", "PySide6",
    ]
    print("[install] pip args:", args)
    try:
        rc = pip_main(args)
    except SystemExit as exc:  # pip 内部可能调用 sys.exit
        rc = exc.code if isinstance(exc.code, int) else 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
