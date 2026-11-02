"""角标悬浮窗: 无边框、置顶、透明、鼠标穿透, 显示当前激活状态的角标。"""
from __future__ import annotations

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import QLabel, QWidget

from .config import FALLBACK_ICONS, resolve_icon_path

# 状态 key -> 中文名
STATUS_NAMES = {
    "stream": "推流",
    "record": "录制",
    "replay": "回放缓存",
    "virtualcam": "虚拟摄像机",
}

DEFAULT_ORDER = ["stream", "record", "replay", "virtualcam"]


class BadgeWindow(QWidget):
    """悬浮角标容器窗口。

    每个状态对应一个 QLabel(图标), 激活时显示, 未激活时隐藏;
    可见角标按 order 顺序, 依 direction 垂直堆叠或水平排列。
    """

    def __init__(self, cfg: dict):
        super().__init__()
        self._labels: dict[str, QLabel] = {}
        self._screen_index = 0
        self._warned_paths: set[str] = set()
        self._setup_window()
        self._create_labels()
        self.update_config(cfg)
        self.set_state({k: False for k in STATUS_NAMES})
        self.show()

    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.FramelessWindowHint          # 无边框
            | Qt.WindowStaysOnTopHint       # 置顶
            | Qt.Tool                       # 不占任务栏
            | Qt.WindowTransparentForInput  # 鼠标穿透
            | Qt.WindowDoesNotAcceptFocus   # 不抢焦点
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setWindowTitle("OBS桌面角标")

    def _create_labels(self) -> None:
        for key in STATUS_NAMES:
            label = QLabel(self)
            label.setAlignment(Qt.AlignCenter)
            label.setScaledContents(True)
            label.hide()
            self._labels[key] = label

    # ------------------------------------------------------------------ #
    def update_config(self, cfg: dict) -> None:
        """应用完整配置, 刷新尺寸/透明度/锚点/排列方式/顺序。"""
        badge = cfg["badge"]
        icons = cfg["icons"]
        self._size = int(badge.get("size", 21))
        self._opacity = float(badge.get("opacity", 1.0))
        self._spacing = int(badge.get("spacing", 8))
        self._anchor = badge.get("anchor", "bottom-right")
        self._screen_index = int(badge.get("screen_index", 0))
        self._offset = QPoint(
            int(badge.get("offset_x", 24)), int(badge.get("offset_y", 24))
        )
        self._direction = badge.get("direction", "vertical")

        order = [k for k in badge.get("order", DEFAULT_ORDER) if k in STATUS_NAMES]
        for key in STATUS_NAMES:  # 兜底: 补上遗漏的状态
            if key not in order:
                order.append(key)
        self._order = order

        self.setWindowOpacity(self._opacity)
        self._reload_icons(icons)
        self._layout_badges()
        self._reposition()

    def _reload_icons(self, icons_cfg: dict) -> None:
        for key, label in self._labels.items():
            rel = icons_cfg.get(key)
            pixmap = self._load_pixmap(rel)
            if pixmap.isNull() and rel:
                # 方案图标缺失/损坏, 兜底到默认方案
                pixmap = self._load_pixmap(FALLBACK_ICONS.get(key))
            if pixmap.isNull():
                label.clear()
            else:
                label.setPixmap(pixmap)
            label.setFixedSize(self._size, self._size)

    def _load_pixmap(self, rel) -> QPixmap:
        """加载图标; 失败时记录一次警告并返回空 QPixmap。"""
        if not rel:
            return QPixmap()
        path = resolve_icon_path(rel)
        pm = QPixmap(str(path))
        if pm.isNull():
            if str(path) not in self._warned_paths:
                self._warned_paths.add(str(path))
                print(f"[badge] 无法加载图标(将用默认方案兜底): {path}")
        else:
            pm = pm.scaled(
                self._size, self._size,
                Qt.KeepAspectRatio, Qt.SmoothTransformation,
            )
        return pm

    # ------------------------------------------------------------------ #
    def set_state(self, status: dict) -> None:
        """按最新状态显示/隐藏各角标, 并重新排列定位。"""
        for key, label in self._labels.items():
            label.setVisible(bool(status.get(key, False)))
        self._layout_badges()
        self._reposition()

    def _layout_badges(self) -> None:
        """手动排列可见角标, 并据此调整容器大小。"""
        visible = [k for k in self._order if self._labels[k].isVisible()]
        n = len(visible)
        s = self._size
        gap = self._spacing

        for i, key in enumerate(visible):
            label = self._labels[key]
            label.setFixedSize(s, s)
            if self._direction == "horizontal":
                label.move(i * (s + gap), 0)
            else:
                label.move(0, i * (s + gap))

        if n == 0:
            self.resize(0, 0)
        elif self._direction == "horizontal":
            self.resize(n * s + (n - 1) * gap, s)
        else:
            self.resize(s, n * s + (n - 1) * gap)

    def _reposition(self) -> None:
        """根据屏幕 + 锚点 + 偏移, 把窗口放到指定显示器的对应位置。"""
        screens = QGuiApplication.screens()
        if not screens:
            return
        idx = self._screen_index
        if idx < 0 or idx >= len(screens):
            idx = 0
        geo = screens[idx].availableGeometry()
        w = self.width()
        h = self.height()

        if "left" in self._anchor:
            x = geo.left() + self._offset.x()
        elif "right" in self._anchor:
            x = geo.right() - w - self._offset.x() + 1
        else:
            x = geo.left() + (geo.width() - w) // 2 + self._offset.x()

        if "top" in self._anchor:
            y = geo.top() + self._offset.y()
        elif "bottom" in self._anchor:
            y = geo.bottom() - h - self._offset.y() + 1
        else:
            y = geo.top() + (geo.height() - h) // 2 + self._offset.y()

        self.move(x, y)
