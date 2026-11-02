"""连接 OBS WebSocket 并查询四种状态, 验证核心链路。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "vendor"))

import obsws_python as obs  # noqa: E402

HOST = "192.168.31.122"
PORT = 4455
PASSWORD = "3141592653589"


def val(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def main():
    print(f"连接 {HOST}:{PORT} ...")
    client = obs.ReqClient(host=HOST, port=PORT, password=PASSWORD, timeout=5)
    print("连接成功")

    checks = {
        "stream": client.get_stream_status,
        "record": client.get_record_status,
        "replay": client.get_replay_buffer_status,
        "virtualcam": client.get_virtual_cam_status,
    }
    for key, fn in checks.items():
        try:
            res = fn()
            active = val(res, "output_active")
            print(f"  {key:12s} output_active = {active}   (原始: {res})")
        except Exception as exc:
            print(f"  {key:12s} 查询失败: {exc}")

    client.disconnect()
    print("已断开")


if __name__ == "__main__":
    main()
