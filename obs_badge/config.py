"""配置加载与保存。"""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

# 密码混淆密钥(仅避免明文落盘, 属简单混淆而非安全加密)
_ENCODE_KEY = "obs-badge-local-v1"

# 图标方案内各状态的图标文件名
ICON_FILENAMES = {
    "stream": "streaming.png",
    "record": "recording.png",
    "replay": "buffering.png",
    "virtualcam": "virtualcam.png",
}

# 方案文件缺失时的兜底图标(默认方案)
FALLBACK_ICONS = {
    "stream": "IconSets/default/streaming.png",
    "record": "IconSets/default/recording.png",
    "replay": "IconSets/default/buffering.png",
    "virtualcam": "IconSets/default/virtualcam.png",
}

DEFAULT_CONFIG = {
    "obs": {
        "host": "127.0.0.1",
        "port": 4455,
        "use_password": False,
        "password": "",
        "timeout": 3.0,         # 单次请求超时(秒)
        "poll_interval": 1.0,   # 状态轮询间隔(秒)
        "retry_interval": 3.0,  # 断线重连间隔(秒)
    },
    "badge": {
        # 九宫格锚点: top-left / top-center / top-right / center-left / center /
        #             center-right / bottom-left / bottom-center / bottom-right
        "screen_index": 0,      # 显示器索引(0 = 主显示器)
        "anchor": "bottom-right",
        "offset_x": 24,         # 距锚点的水平偏移(像素)
        "offset_y": 24,         # 距锚点的垂直偏移(像素)
        "size": 21,             # 角标显示尺寸(像素, 等比缩放)
        "opacity": 1.0,         # 整体透明度 0.0~1.0
        "spacing": 8,           # 多个角标之间的间距(像素)
        "direction": "vertical",  # 多角标排列: vertical(垂直堆叠) / horizontal(水平排列)
        "order": ["stream", "record", "replay", "virtualcam"],  # 角标显示顺序
    },
    "icons": {
        "icon_set": "default",  # 当前图标方案名(IconSets 下的文件夹)
        "stream": "IconSets/default/streaming.png",
        "record": "IconSets/default/recording.png",
        "replay": "IconSets/default/buffering.png",
        "virtualcam": "IconSets/default/virtualcam.png",
    },
    "autostart": {
        "low_priority": True,      # 以较低优先级运行
        "minimize_to_tray": True,  # 启动后自动最小化到托盘
        "close_to_tray": True,     # 点击关闭时最小化到托盘
    },
}

def _get_project_root() -> Path:
    """项目根目录: 开发时为源码根目录, 打包后为 exe 所在目录。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


PROJECT_ROOT = _get_project_root()
CONFIG_PATH = PROJECT_ROOT / "config.json"


def _obfuscate(plain: str) -> str:
    """简单混淆: XOR + base64。"""
    if not plain:
        return ""
    key = _ENCODE_KEY.encode("utf-8")
    data = plain.encode("utf-8")
    xored = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
    return base64.urlsafe_b64encode(xored).decode("ascii")


def _deobfuscate(encoded: str) -> str:
    if not encoded:
        return ""
    try:
        xored = base64.urlsafe_b64decode(encoded.encode("ascii"))
        key = _ENCODE_KEY.encode("utf-8")
        data = bytes(b ^ key[i % len(key)] for i, b in enumerate(xored))
        return data.decode("utf-8")
    except Exception:  # noqa: BLE001
        return ""


def scan_icon_sets() -> list[str]:
    """扫描 IconSets 目录, 返回方案名列表(文件夹名, 排序)。"""
    sets_dir = PROJECT_ROOT / "IconSets"
    if not sets_dir.is_dir():
        return []
    return sorted(p.name for p in sets_dir.iterdir() if p.is_dir())


def icon_set_dir(set_name: str) -> Path:
    """返回方案文件夹路径。"""
    return PROJECT_ROOT / "IconSets" / set_name


def icon_set_paths(set_name: str) -> dict[str, str]:
    """返回方案内各状态图标路径(相对项目根的路径, 缺失文件用兜底图标)。"""
    result: dict[str, str] = {}
    base = icon_set_dir(set_name)
    for key, fname in ICON_FILENAMES.items():
        p = base / fname
        if p.is_file():
            result[key] = f"IconSets/{set_name}/{fname}"
        else:
            result[key] = FALLBACK_ICONS[key]
    return result


def load_icon_set_badge(set_name: str) -> dict:
    """加载方案文件夹内的独立外观配置 {size, opacity, spacing}。"""
    path = icon_set_dir(set_name) / "badge.json"
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return {
                "size": int(data.get("size", 21)),
                "opacity": float(data.get("opacity", 1.0)),
                "spacing": int(data.get("spacing", 8)),
            }
        except Exception as exc:  # noqa: BLE001
            print(f"[config] 读取方案配置失败 {path}: {exc}")
    return {}


def save_icon_set_badge(set_name: str, badge: dict) -> None:
    """保存方案文件夹内的独立外观配置(仅 size/opacity/spacing)。"""
    d = icon_set_dir(set_name)
    d.mkdir(parents=True, exist_ok=True)
    path = d / "badge.json"
    data = {
        "size": int(badge.get("size", 21)),
        "opacity": float(badge.get("opacity", 1.0)),
        "spacing": int(badge.get("spacing", 8)),
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _apply_icon_set(cfg: dict) -> None:
    """按当前方案名刷新 icons 里的四个状态路径。"""
    icons = cfg.get("icons", {})
    set_name = icons.get("icon_set") or "default"
    icons.update(icon_set_paths(set_name))


def _apply_icon_set_badge(cfg: dict) -> None:
    """把当前方案文件夹内的独立外观配置合并到 badge。"""
    set_name = cfg.get("icons", {}).get("icon_set") or "default"
    extra = load_icon_set_badge(set_name)
    if extra:
        cfg["badge"].update(extra)


def load_config() -> dict:
    """读取 config.json, 缺失项用默认值补齐; 解密已保存的密码。"""
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))  # 深拷贝默认配置
    if CONFIG_PATH.exists():
        try:
            user = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            obs = user.get("obs", {})
            if isinstance(obs, dict) and "password_enc" in obs:
                obs["password"] = _deobfuscate(obs.pop("password_enc") or "")
            _merge(cfg, user)
        except Exception as exc:  # noqa: BLE001
            print(f"[config] 读取 config.json 失败, 使用默认配置: {exc}")
    _apply_icon_set(cfg)
    _apply_icon_set_badge(cfg)
    return cfg


def save_config(cfg: dict) -> None:
    """写回 config.json; 密码混淆后落盘(不存明文)。"""
    out = json.loads(json.dumps(cfg))
    obs = out.get("obs", {})
    if isinstance(obs, dict):
        if obs.get("password"):
            obs["password_enc"] = _obfuscate(str(obs["password"]))
        obs.pop("password", None)
    CONFIG_PATH.write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def resolve_icon_path(rel: str) -> Path:
    """把相对路径解析为基于项目根目录的绝对路径。"""
    p = Path(rel)
    if p.is_absolute():
        return p
    return PROJECT_ROOT / p


def _merge(base: dict, override: dict) -> None:
    """递归合并, override 覆盖 base。"""
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value
