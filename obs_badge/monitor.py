"""OBS 状态监视器: 通过 obs-websocket 轮询四种输出状态。

四种状态:
  - stream     : 直播(推流)中
  - record     : 录制中
  - replay     : 回放缓存已开启
  - virtualcam : 虚拟摄像机已开启
"""
from __future__ import annotations

import logging

from PySide6.QtCore import QThread, Signal

import obsws_python as obs
from obsws_python.error import OBSSDKError, OBSSDKRequestError

# 抑制 obsws-python 内部 logger.exception 产生的 traceback 日志噪音
logging.getLogger("obsws_python").setLevel(logging.CRITICAL)

STATUS_KEYS = ("stream", "record", "replay", "virtualcam")


def _value(obj, key, default=None):
    """兼容 dict 与对象属性两种取值方式。"""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _friendly_error(exc: Exception) -> str:
    """把异常转成用户友好的提示信息。"""
    if isinstance(exc, OBSSDKError):
        return "密码错误，请检查 WebSocket 密码是否正确"
    if isinstance(exc, ConnectionRefusedError):
        code = getattr(exc, "winerror", None) or getattr(exc, "errno", None)
        suffix = f"(WinError {code})" if code else ""
        return f"可能是OBS未开启WebSocket或者链接凭证有误{suffix}"
    if "getaddrinfo" in str(exc):
        return "无法解析服务器地址，请检查地址是否正确"
    code = getattr(exc, "winerror", None) or getattr(exc, "errno", None)
    suffix = f"(WinError {code})" if code else ""
    return f"无法连接到OBS{suffix}"


class ObsMonitor(QThread):
    """后台线程: 连接 OBS WebSocket, 周期轮询状态并通过信号上报。

    信号:
      status_changed(dict)     -> {"stream": bool, "record": bool, "replay": bool, "virtualcam": bool}
      connection_changed(bool) -> True 表示已连接
      error(str)               -> 连接失败/中断的具体错误信息
    """

    status_changed = Signal(dict)
    connection_changed = Signal(bool)
    error = Signal(str)

    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent)
        obs_cfg = cfg["obs"]
        self._host = obs_cfg["host"]
        self._port = int(obs_cfg["port"])
        self._use_password = bool(obs_cfg.get("use_password", True))
        self._password = obs_cfg.get("password", "") or ""
        self._timeout = float(obs_cfg.get("timeout", 3.0))
        self._poll_interval = float(obs_cfg.get("poll_interval", 1.0))
        self._retry_interval = float(obs_cfg.get("retry_interval", 3.0))
        self._running = True

    def stop(self) -> None:
        """请求线程停止(线程会在此次轮询后退出)。"""
        self._running = False

    def run(self) -> None:  # noqa: D102
        while self._running:
            client = None
            try:
                password = self._password if self._use_password else ""
                client = obs.ReqClient(
                    host=self._host,
                    port=self._port,
                    password=password,
                    timeout=self._timeout,
                )
                self.connection_changed.emit(True)
                print(f"[monitor] 已连接 OBS WebSocket: {self._host}:{self._port}")
                while self._running:
                    status = self._poll(client)
                    self.status_changed.emit(status)
                    self.msleep(int(self._poll_interval * 1000))
            except Exception as exc:  # noqa: BLE001
                print(f"[monitor] 连接异常: {type(exc).__name__}: {exc}")
                self.connection_changed.emit(False)
                self.error.emit(_friendly_error(exc))
                # 连接不可用时, 所有状态置为未激活
                self.status_changed.emit({k: False for k in STATUS_KEYS})
            finally:
                try:
                    if client is not None:
                        client.disconnect()
                except Exception:  # noqa: BLE001
                    pass

            if self._running:
                self.msleep(int(self._retry_interval * 1000))

    def _poll(self, client) -> dict:
        """查询四种输出状态。

        207(OBS 未就绪)不算错误: 保持连接, 下次轮询再试;
        仅当全部查询都真正失败时才视为连接断开。
        """
        pollers = {
            "stream": client.get_stream_status,
            "record": client.get_record_status,
            "replay": client.get_replay_buffer_status,
            "virtualcam": client.get_virtual_cam_status,
        }
        status = {}
        errors = 0
        for key, fn in pollers.items():
            try:
                res = fn()
                status[key] = bool(_value(res, "output_active"))
            except OBSSDKRequestError as exc:
                if getattr(exc, "code", None) == 207:  # OBS 未就绪
                    status[key] = False
                else:
                    errors += 1
                    print(f"[monitor] 查询状态 {key} 失败: {exc}")
                    status[key] = False
            except Exception as exc:  # noqa: BLE001
                errors += 1
                print(f"[monitor] 查询状态 {key} 失败: {exc}")
                status[key] = False
        if errors == len(pollers):
            raise ConnectionError("所有状态查询均失败")
        return status
