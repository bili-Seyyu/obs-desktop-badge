"""设置窗口: 配置连接、图标方案、角标外观、位置、排列方式与顺序。"""
from __future__ import annotations

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .badge_window import STATUS_NAMES
from .config import PROJECT_ROOT, icon_set_dir, scan_icon_sets

# 九宫格锚点(行优先: 上左->上中->上右->...)
ANCHOR_ITEMS = [
    ("top-left", "左上"),
    ("top-center", "上中"),
    ("top-right", "右上"),
    ("center-left", "左中"),
    ("center", "居中"),
    ("center-right", "右中"),
    ("bottom-left", "左下"),
    ("bottom-center", "下中"),
    ("bottom-right", "右下"),
]

HELP_TEXT = (
    "OBS WebSocket 配置步骤：\n\n"
    "1. 打开 OBS Studio\n"
    "2. 菜单「工具」→「WebSocket 服务器设置」\n"
    "3. 勾选「启用 WebSocket 服务器」\n"
    "4. 点击「显示连接信息」查看服务器地址与端口\n"
    "5. 若设置了服务器密码，请在本窗口勾选「启用密码验证」并填写密码\n"
    "6. 回到本窗口填写地址/端口后点击「链接」\n\n"
    "说明：OBS 28+ 已内置 WebSocket，无需额外安装插件。"
)


class SettingsWindow(QWidget):
    """设置窗口。任何控件变化都会 emit 最新的配置; 连接相关通过信号通知主程序。"""

    config_changed = Signal(dict)           # badge 配置
    icon_set_changed = Signal(str)          # 图标方案名
    connect_requested = Signal(dict)        # obs 配置 {host, port, use_password, password}
    preview_changed = Signal(bool)
    autostart_changed = Signal(dict)        # {low_priority, minimize_to_tray, close_to_tray}
    generate_script_clicked = Signal()
    window_closed = Signal()

    def __init__(self, cfg: dict):
        super().__init__()
        self.setWindowTitle("OBS桌面角标 - 设置")
        self.setMinimumWidth(700)
        self._badge = cfg.get("badge", {})
        self._obs = cfg.get("obs", {})
        self._icons = cfg.get("icons", {})
        self._autostart = cfg.get("autostart", {})
        self._anchor_buttons: dict[str, QPushButton] = {}
        self._default_screen_index = self._find_default_screen_index()
        self._build_ui()
        self._connect_signals()
        self._load_values()

    # ------------------------------------------------------------------ #
    @staticmethod
    def _find_default_screen_index() -> int:
        screens = QGuiApplication.screens()
        primary = QGuiApplication.primaryScreen()
        for i, s in enumerate(screens):
            if s is primary:
                return i
        return 0

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        # 连接状态(顶部横跨)
        self.status_label = QLabel("正在连接…")
        self.status_label.setStyleSheet("color: gray; font-weight: bold;")
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)

        # 两列
        columns = QHBoxLayout()
        left = QVBoxLayout()
        right = QVBoxLayout()

        # ---- 左列: WebSocket 连接 + 外观 ----
        conn = QGroupBox("WebSocket 连接")
        cform = QFormLayout(conn)
        self.host_edit = QLineEdit()
        cform.addRow("地址", self.host_edit)

        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        cform.addRow("端口", self.port_spin)

        self.use_password_check = QCheckBox("启用密码验证")
        cform.addRow("", self.use_password_check)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        cform.addRow("密码", self.password_edit)

        btn_row = QHBoxLayout()
        self.help_btn = QPushButton("帮助")
        self.connect_btn = QPushButton("链接")
        self.connect_btn.setDefault(True)
        btn_row.addWidget(self.help_btn)
        btn_row.addWidget(self.connect_btn)
        cform.addRow("", btn_row)
        left.addWidget(conn)

        appearance = QGroupBox("外观")
        form = QFormLayout(appearance)
        icon_row = QHBoxLayout()
        self.icon_set_combo = QComboBox()
        self.refresh_icon_btn = QPushButton("刷新")
        self.open_folder_btn = QPushButton("打开文件夹")
        icon_row.addWidget(self.icon_set_combo, 1)
        icon_row.addWidget(self.refresh_icon_btn)
        icon_row.addWidget(self.open_folder_btn)
        form.addRow("图标方案", icon_row)

        self.size_spin = QSpinBox()
        self.size_spin.setRange(8, 512)
        self.size_spin.setSuffix(" px")
        form.addRow("角标尺寸", self.size_spin)

        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(10, 100)
        self.opacity_value = QLabel()
        op_row = QHBoxLayout()
        op_row.addWidget(self.opacity_slider, 1)
        op_row.addWidget(self.opacity_value)
        form.addRow("透明度", op_row)

        self.spacing_spin = QSpinBox()
        self.spacing_spin.setRange(0, 200)
        self.spacing_spin.setSuffix(" px")
        form.addRow("角标间距", self.spacing_spin)
        left.addWidget(appearance)
        left.addStretch(1)

        # ---- 右列: 屏幕位置 + 排列 ----
        position = QGroupBox("屏幕位置")
        pform = QFormLayout(position)
        self.screen_combo = QComboBox()
        for i, s in enumerate(QGuiApplication.screens()):
            geo = s.geometry()
            text = f"屏幕 {i + 1} ({geo.width()}×{geo.height()})"
            if s is QGuiApplication.primaryScreen():
                text += "（主）"
            self.screen_combo.addItem(text, i)
        pform.addRow("显示器", self.screen_combo)

        self.anchor_group = QButtonGroup(self)
        self.anchor_group.setExclusive(True)
        grid = QGridLayout()
        grid.setSpacing(4)
        for i, (value, label) in enumerate(ANCHOR_ITEMS):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedSize(46, 32)
            grid.addWidget(btn, i // 3, i % 3)
            self.anchor_group.addButton(btn, i)
            self._anchor_buttons[value] = btn
        pform.addRow("锚点", grid)

        self.offset_x_spin = QSpinBox()
        self.offset_x_spin.setRange(-5000, 5000)
        self.offset_x_spin.setSuffix(" px")
        pform.addRow("水平偏移", self.offset_x_spin)

        self.offset_y_spin = QSpinBox()
        self.offset_y_spin.setRange(-5000, 5000)
        self.offset_y_spin.setSuffix(" px")
        pform.addRow("垂直偏移", self.offset_y_spin)
        right.addWidget(position)

        arrange = QGroupBox("排列")
        aform = QFormLayout(arrange)
        self.direction_combo = QComboBox()
        self.direction_combo.addItem("竖排", "vertical")
        self.direction_combo.addItem("横排", "horizontal")
        aform.addRow("排列方式", self.direction_combo)

        self.order_list = QListWidget()
        self.order_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.order_list.setDefaultDropAction(Qt.MoveAction)
        self.order_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.order_list.setFixedHeight(120)
        aform.addRow("角标顺序", self.order_list)

        hint = QLabel("拖动列表项可调整角标排列顺序")
        hint.setStyleSheet("color: gray;")
        aform.addRow("", hint)
        right.addWidget(arrange)
        right.addStretch(1)

        columns.addLayout(left)
        columns.addLayout(right)
        root.addLayout(columns)

        # 预览开关
        self.preview_check = QCheckBox("预览角标（无视当前状态显示全部）")
        root.addWidget(self.preview_check)

        # 随OBS启动
        autostart = QGroupBox("随OBS启动")
        auto_form = QVBoxLayout(autostart)
        help_row = QHBoxLayout()
        help_label = QLabel("帮助")
        self.autostart_help_btn = QPushButton("?")
        self.autostart_help_btn.setFixedSize(24, 24)
        self.autostart_help_btn.setToolTip("查看帮助")
        help_row.addWidget(help_label)
        help_row.addWidget(self.autostart_help_btn)
        help_row.addStretch(1)
        auto_form.addLayout(help_row)

        self.low_priority_check = QCheckBox("以较低优先级运行")
        auto_form.addWidget(self.low_priority_check)
        self.minimize_check = QCheckBox("启动后自动最小化到托盘")
        auto_form.addWidget(self.minimize_check)
        self.close_to_tray_check = QCheckBox("点击关闭时最小化到托盘")
        auto_form.addWidget(self.close_to_tray_check)

        self.script_btn = QPushButton("生成启动脚本")
        auto_form.addWidget(self.script_btn)
        root.addWidget(autostart)

        # 关于
        about = QGroupBox("关于")
        about_form = QVBoxLayout(about)
        nick = QLabel("作者：四羽Seyyu")
        about_form.addWidget(nick)
        link = QLabel(
            '<a href="https://space.bilibili.com/84125742">'
            'bilibili 主页：https://space.bilibili.com/84125742</a>'
        )
        link.setOpenExternalLinks(True)
        link.setTextFormat(Qt.RichText)
        about_form.addWidget(link)
        decl = QLabel("声明：本软件完全免费，可商用使用，禁止二次分发")
        decl.setWordWrap(True)
        about_form.addWidget(decl)
        root.addWidget(about)

    def _connect_signals(self) -> None:
        self.help_btn.clicked.connect(self._show_help)
        self.connect_btn.clicked.connect(self._on_connect)
        self.use_password_check.toggled.connect(self.password_edit.setEnabled)
        self.preview_check.toggled.connect(self.preview_changed)
        self.script_btn.clicked.connect(lambda *_a: self.generate_script_clicked.emit())
        self.autostart_help_btn.clicked.connect(self._show_autostart_help)
        self.low_priority_check.toggled.connect(self._emit_autostart)
        self.minimize_check.toggled.connect(self._emit_autostart)
        self.close_to_tray_check.toggled.connect(self._emit_autostart)

        self.icon_set_combo.currentIndexChanged.connect(self._on_icon_set_changed)
        self.refresh_icon_btn.clicked.connect(self._refresh_icon_sets)
        self.open_folder_btn.clicked.connect(self._open_icon_folder)
        self.screen_combo.currentIndexChanged.connect(self._emit)
        self.anchor_group.buttonClicked.connect(self._on_anchor_clicked)
        self.size_spin.valueChanged.connect(self._emit)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        self.spacing_spin.valueChanged.connect(self._emit)
        self.offset_x_spin.valueChanged.connect(self._emit)
        self.offset_y_spin.valueChanged.connect(self._emit)
        self.direction_combo.currentIndexChanged.connect(self._emit)
        self.order_list.model().rowsMoved.connect(self._on_order_moved)

    # ------------------------------------------------------------------ #
    def _show_help(self) -> None:
        QMessageBox.information(self, "WebSocket 配置帮助", HELP_TEXT)

    def _show_autostart_help(self) -> None:
        QMessageBox.information(
            self,
            "随OBS启动帮助",
            "点击「生成启动脚本」后，根目录会生成 obs_badge_autostart.lua 文件。\n"
            "将根目录中生成的 obs_badge_autostart.lua 加载到 OBS 中。\n"
            "位置：工具 - 脚本 - \"+\"\n\n"
            "加载后：OBS 启动时自动运行本软件。",
        )

    def _emit_autostart(self, *_args) -> None:
        self.autostart_changed.emit({
            "low_priority": self.low_priority_check.isChecked(),
            "minimize_to_tray": self.minimize_check.isChecked(),
            "close_to_tray": self.close_to_tray_check.isChecked(),
        })

    def _on_connect(self) -> None:
        self.connect_requested.emit(self.collect_obs_config())

    def collect_obs_config(self) -> dict:
        return {
            "host": self.host_edit.text().strip(),
            "port": self.port_spin.value(),
            "use_password": self.use_password_check.isChecked(),
            "password": self.password_edit.text(),
        }

    def set_status(self, text: str, is_error: bool = False) -> None:
        """更新连接状态显示(不弹窗)。"""
        self.status_label.setText(text)
        color = "red" if is_error else "#2e7d32"
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")

    def set_connecting(self, connecting: bool) -> None:
        """连接中禁用链接按钮, 防止反复点击。"""
        self.connect_btn.setEnabled(not connecting)

    # ---- 图标方案 ----------------------------------------------------- #
    def _populate_icon_sets(self) -> None:
        self.icon_set_combo.clear()
        for name in scan_icon_sets():
            self.icon_set_combo.addItem(name, name)

    def _refresh_icon_sets(self) -> None:
        current = self.icon_set_combo.currentData()
        self.icon_set_combo.blockSignals(True)
        self._populate_icon_sets()
        idx = self.icon_set_combo.findData(current)
        if idx < 0:
            idx = 0
        self.icon_set_combo.setCurrentIndex(idx)
        self.icon_set_combo.blockSignals(False)
        self._on_icon_set_changed()

    def _on_icon_set_changed(self, *_args) -> None:
        name = self.icon_set_combo.currentData()
        if name:
            self.icon_set_changed.emit(name)

    def _open_icon_folder(self) -> None:
        name = self.icon_set_combo.currentData()
        if not name:
            return
        path = icon_set_dir(name)
        if not path.is_dir():
            path = PROJECT_ROOT / "IconSets"
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def update_appearance(self, size: int, opacity: float, spacing: int) -> None:
        """切换方案后, 把该方案的独立外观配置同步到控件(不触发保存)。"""
        self.size_spin.blockSignals(True)
        self.opacity_slider.blockSignals(True)
        self.spacing_spin.blockSignals(True)
        self.size_spin.setValue(int(size))
        pct = int(float(opacity) * 100)
        self.opacity_slider.setValue(pct)
        self.opacity_value.setText(f"{pct}%")
        self.spacing_spin.setValue(int(spacing))
        self.size_spin.blockSignals(False)
        self.opacity_slider.blockSignals(False)
        self.spacing_spin.blockSignals(False)

    # ------------------------------------------------------------------ #
    def _on_opacity_changed(self, value: int) -> None:
        self.opacity_value.setText(f"{value}%")
        self._emit()

    def _on_anchor_clicked(self, *_args) -> None:
        self._emit()

    def _on_order_moved(self, *_args) -> None:
        self._emit()

    def _current_anchor(self) -> str:
        idx = self.anchor_group.checkedId()
        if 0 <= idx < len(ANCHOR_ITEMS):
            return ANCHOR_ITEMS[idx][0]
        return "bottom-right"

    # ------------------------------------------------------------------ #
    def _load_values(self) -> None:
        # obs
        self.host_edit.setText(str(self._obs.get("host", "127.0.0.1")))
        self.port_spin.setValue(int(self._obs.get("port", 4455)))
        use_pw = bool(self._obs.get("use_password", True))
        self.use_password_check.setChecked(use_pw)
        self.password_edit.setText(str(self._obs.get("password", "")))
        self.password_edit.setEnabled(use_pw)

        # autostart
        auto_checks = (
            self.low_priority_check, self.minimize_check,
            self.close_to_tray_check,
        )
        for w in auto_checks:
            w.blockSignals(True)
        self.low_priority_check.setChecked(bool(self._autostart.get("low_priority", True)))
        self.minimize_check.setChecked(bool(self._autostart.get("minimize_to_tray", True)))
        self.close_to_tray_check.setChecked(bool(self._autostart.get("close_to_tray", True)))
        for w in auto_checks:
            w.blockSignals(False)

        # 图标方案
        self.icon_set_combo.blockSignals(True)
        self._populate_icon_sets()
        current_set = self._icons.get("icon_set", "default")
        idx = self.icon_set_combo.findData(current_set)
        if idx < 0:
            idx = 0
        self.icon_set_combo.setCurrentIndex(idx)
        self.icon_set_combo.blockSignals(False)

        # badge
        b = self._badge
        widgets = (
            self.screen_combo, self.size_spin, self.opacity_slider,
            self.spacing_spin, self.offset_x_spin, self.offset_y_spin,
            self.direction_combo,
        )
        for w in widgets:
            w.blockSignals(True)

        idx = self.screen_combo.findData(int(b.get("screen_index", self._default_screen_index)))
        if idx < 0:
            idx = self.screen_combo.findData(self._default_screen_index)
            if idx < 0:
                idx = 0
        self.screen_combo.setCurrentIndex(idx)

        self.size_spin.setValue(int(b.get("size", 21)))
        self.opacity_slider.setValue(int(float(b.get("opacity", 1.0)) * 100))
        self.spacing_spin.setValue(int(b.get("spacing", 8)))
        self.offset_x_spin.setValue(int(b.get("offset_x", 24)))
        self.offset_y_spin.setValue(int(b.get("offset_y", 24)))
        idx = self.direction_combo.findData(b.get("direction", "vertical"))
        self.direction_combo.setCurrentIndex(idx if idx >= 0 else 0)

        # 锚点九宫格
        anchor = b.get("anchor", "bottom-right")
        target_id = -1
        for i, (value, _label) in enumerate(ANCHOR_ITEMS):
            if value == anchor:
                target_id = i
                break
        if target_id >= 0:
            self.anchor_group.button(target_id).setChecked(True)

        # 顺序列表
        self.order_list.blockSignals(True)
        self.order_list.clear()
        existing: list[str] = []
        for key in b.get("order", []) or []:
            if key in STATUS_NAMES:
                item = QListWidgetItem(STATUS_NAMES[key])
                item.setData(Qt.UserRole, key)
                self.order_list.addItem(item)
                existing.append(key)
        for key in STATUS_NAMES:  # 兜底补全
            if key not in existing:
                item = QListWidgetItem(STATUS_NAMES[key])
                item.setData(Qt.UserRole, key)
                self.order_list.addItem(item)
        self.opacity_value.setText(f"{self.opacity_slider.value()}%")

        for w in widgets:
            w.blockSignals(False)
        self.order_list.blockSignals(False)

    def _emit(self) -> None:
        order = [
            self.order_list.item(i).data(Qt.UserRole)
            for i in range(self.order_list.count())
        ]
        self.config_changed.emit({
            "screen_index": self.screen_combo.currentData(),
            "anchor": self._current_anchor(),
            "size": self.size_spin.value(),
            "opacity": self.opacity_slider.value() / 100.0,
            "spacing": self.spacing_spin.value(),
            "offset_x": self.offset_x_spin.value(),
            "offset_y": self.offset_y_spin.value(),
            "direction": self.direction_combo.currentData(),
            "order": order,
        })

    def closeEvent(self, event) -> None:  # noqa: N802
        """关闭设置窗口即通知主程序(由主程序决定退出或最小化到托盘)。"""
        self.window_closed.emit()
        event.accept()
