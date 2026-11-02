"""OBS 桌面角标 —— 程序入口。

运行: py -3.14 main.py
启动后: 屏幕悬浮显示状态角标, 弹出设置窗口; 关闭设置窗口即退出程序。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# pythonw.exe(无控制台)下 stdout/stderr 为 None, 重定向到 devnull 避免 print 报错
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

# 让 Python 能导入工作目录下 vendor 里的第三方依赖(开发期运行方式)
sys.path.insert(0, str(Path(__file__).resolve().parent / "vendor"))

from PySide6.QtCore import QSharedMemory  # noqa: E402
from PySide6.QtGui import QIcon  # noqa: E402
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon  # noqa: E402

from obs_badge.autostart import generate_script  # noqa: E402
from obs_badge.badge_window import BadgeWindow  # noqa: E402
from obs_badge.config import (  # noqa: E402
    PROJECT_ROOT,
    icon_set_paths,
    load_config,
    load_icon_set_badge,
    save_config,
    save_icon_set_badge,
)
from obs_badge.monitor import STATUS_KEYS, ObsMonitor  # noqa: E402
from obs_badge.settings_window import SettingsWindow  # noqa: E402


def _app_icon() -> QIcon:
    ico = PROJECT_ROOT / "icon.ico"
    if ico.is_file():
        return QIcon(str(ico))
    return QIcon()


def _extract_obs_pid(argv: list) -> int | None:
    """从命令行参数中提取 --obs-pid 值, 并从 argv 中移除该参数。"""
    pid = None
    filtered: list = []
    i = 0
    while i < len(argv):
        if argv[i] == "--obs-pid" and i + 1 < len(argv):
            try:
                pid = int(argv[i + 1])
            except ValueError:
                pid = None
            i += 2
        else:
            filtered.append(argv[i])
            i += 1
    argv[:] = filtered
    return pid


def main() -> int:
    obs_pid = _extract_obs_pid(sys.argv)
    app = QApplication(sys.argv)
    app.setApplicationName("OBS桌面角标")
    app.setWindowIcon(_app_icon())
    app.setQuitOnLastWindowClosed(False)

    # 单实例限制: 已有实例运行时, 新实例直接退出
    shared = QSharedMemory("obs-badge-single-instance")
    if not shared.create(1):
        print("[main] 已有实例在运行, 本实例退出")
        return 0

    cfg = load_config()

    badge = BadgeWindow(cfg)
    settings = SettingsWindow(cfg)
    settings.setWindowIcon(_app_icon())

    monitor: ObsMonitor | None = None
    last_status: dict = {k: False for k in STATUS_KEYS}
    preview_enabled = False

    # ------------------------------------------------------------------ #
    def apply_status(status: dict) -> None:
        nonlocal last_status
        last_status = status
        if preview_enabled:
            badge.set_state({k: True for k in STATUS_KEYS})
        else:
            badge.set_state(status)

    def on_config_changed(badge_cfg: dict) -> None:
        cfg["badge"] = badge_cfg
        badge.update_config(cfg)
        # 外观配置(size/opacity/spacing)随方案独立保存
        set_name = cfg["icons"].get("icon_set") or "default"
        save_icon_set_badge(set_name, badge_cfg)
        save_config(cfg)

    def on_icon_set_changed(set_name: str) -> None:
        cfg["icons"]["icon_set"] = set_name
        cfg["icons"].update(icon_set_paths(set_name))
        # 加载该方案的独立外观配置
        extra = load_icon_set_badge(set_name)
        if extra:
            cfg["badge"].update(extra)
        badge.update_config(cfg)
        save_config(cfg)
        # 同步外观控件为该方案的值
        settings.update_appearance(
            cfg["badge"].get("size", 21),
            cfg["badge"].get("opacity", 1.0),
            cfg["badge"].get("spacing", 8),
        )

    def restart_monitor() -> None:
        nonlocal monitor
        if monitor is not None:
            monitor.stop()
            monitor.wait(3000)
        monitor = ObsMonitor(cfg)
        monitor.status_changed.connect(apply_status)
        monitor.connection_changed.connect(on_connection_changed)
        monitor.error.connect(on_monitor_error)
        monitor.start()

    def on_connection_changed(ok: bool) -> None:
        settings.set_connecting(False)
        if ok:
            settings.set_status("已连接", False)
            save_config(cfg)  # 连接成功后持久化(密码混淆落盘)

    def on_monitor_error(msg: str) -> None:
        settings.set_connecting(False)
        settings.set_status(f"链接失败\n{msg}", True)

    def on_connect_requested(obs_cfg: dict) -> None:
        cfg["obs"] = obs_cfg
        settings.set_status("连接中…", False)
        settings.set_connecting(True)
        restart_monitor()

    def on_preview_changed(enabled: bool) -> None:
        nonlocal preview_enabled
        preview_enabled = enabled
        apply_status(last_status)

    def on_generate_script() -> None:
        try:
            low_priority = cfg["autostart"].get("low_priority", True)
            path = generate_script(low_priority=low_priority)
            settings.set_status(f"已生成启动脚本: {path.name}", False)
        except Exception as exc:  # noqa: BLE001
            settings.set_status(f"生成脚本失败: {exc}", True)

    def on_autostart_changed(autostart_cfg: dict) -> None:
        cfg["autostart"].update(autostart_cfg)
        save_config(cfg)

    def on_window_closed() -> None:
        if cfg["autostart"].get("close_to_tray", True):
            pass  # 最小化到托盘(窗口已隐藏), 仅托盘"退出"才结束程序
        else:
            app.quit()

    # ------------------------------------------------------------------ #
    settings.config_changed.connect(on_config_changed)
    settings.icon_set_changed.connect(on_icon_set_changed)
    settings.connect_requested.connect(on_connect_requested)
    settings.preview_changed.connect(on_preview_changed)
    settings.generate_script_clicked.connect(on_generate_script)
    settings.autostart_changed.connect(on_autostart_changed)
    settings.window_closed.connect(on_window_closed)

    restart_monitor()

    # 系统托盘
    def show_settings(*_args) -> None:
        settings.show()
        settings.raise_()
        settings.activateWindow()

    tray = QSystemTrayIcon(_app_icon())
    tray.setToolTip("OBS桌面角标")
    menu = QMenu()
    act_settings = menu.addAction("设置")
    act_settings.triggered.connect(show_settings)
    menu.addSeparator()
    act_quit = menu.addAction("退出")
    act_quit.triggered.connect(app.quit)
    tray.setContextMenu(menu)
    tray.activated.connect(
        lambda reason: show_settings() if reason == QSystemTrayIcon.Trigger else None
    )
    tray.show()

    minimize = cfg["autostart"].get("minimize_to_tray", True)
    if not (obs_pid and minimize):
        settings.show()
    print("[main] 角标已启动。关闭设置窗口或托盘「退出」可结束程序。")

    try:
        ret = app.exec()
    finally:
        if monitor is not None:
            monitor.stop()
            monitor.wait(3000)
    return ret


if __name__ == "__main__":
    sys.exit(main())
