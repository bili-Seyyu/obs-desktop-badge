# OBS 桌面角标

在屏幕上悬浮显示 OBS 当前状态角标（直播、录制、回放缓存、虚拟摄像机），类似 NVIDIA 录像/回放状态角标。基于 OBS 内置的 WebSocket（obs-websocket）读取状态，纯本地运行，不上传任何数据。

## 功能特性

- **四种状态实时显示**：推流/直播、录制、回放缓存、虚拟摄像机
- **高度可定制**：
  - 锚点九宫格定位、多显示器选择、偏移、大小、透明度、间距
  - 排列方式（竖排/横排）与角标顺序（拖拽调整）
  - 多套图标方案，可自由切换与自定义
- **预览模式**：无视当前 OBS 状态，一键显示全部角标，方便调整位置
- **随 OBS 启动**：生成 OBS Lua 启动脚本，OBS 启动时自动拉起角标程序
- **设置项自动保存**，每个图标方案可独立保存外观配置
- 系统托盘驻留，界面两列布局

## 系统要求

- Windows 10/11（64 位）
- OBS Studio **28+**（已内置 WebSocket 服务器）
- 运行 exe 版本无需安装 Python；从源码运行需要 Python 3.10+

## 快速开始

### 方式一：下载 exe（推荐普通用户）

到 [Releases](https://github.com/你的用户名/你的仓库名/releases) 页面下载最新压缩包，解压后得到：

```
OBS桌面角标.exe
IconSets/        ← 图标方案
icon.ico
```

双击 `OBS桌面角标.exe` 即可运行。首次运行生成 `config.json`（默认连接 `127.0.0.1:4455`）。

### 方式二：从源码运行

```powershell
# 安装依赖到 vendor/ 目录(不污染全局环境)
py -3.14 install_deps.py

# 运行
py -3.14 main.py
```

## 配置 OBS WebSocket

1. 打开 OBS Studio
2. 菜单「工具」→「WebSocket 服务器设置」
3. 勾选「启用 WebSocket 服务器」
4. 点击「显示连接信息」查看地址与端口（默认 `127.0.0.1:4455`）
5. 如设置了密码，在角标程序「WebSocket 连接」中勾选「启用密码验证」并填写
6. 点击「链接」

程序内「WebSocket 连接」区域的「?」按钮也有相同步骤说明。

## 随 OBS 启动

在设置窗口「随OBS启动」区域：

1. 点击「生成启动脚本」，会在程序根目录生成 `obs_badge_autostart.lua`
2. 在 OBS 中打开「工具 → 脚本」，点击「+」，选择该 `.lua` 文件
3. 之后 OBS 启动时自动运行角标程序

可配置「以较低优先级运行」（默认开）「启动后自动最小化到托盘」（默认开）「点击关闭时最小化到托盘」（默认开）。

## 图标方案

`IconSets/` 下每个文件夹是一个方案，按约定命名图标文件：

| 状态 | 文件名 |
|---|---|
| 推流/直播 | `streaming.png` |
| 录制 | `recording.png` |
| 回放缓存 | `buffering.png` |
| 虚拟摄像机 | `virtualcam.png` |

在「外观 → 图标方案」中切换；「刷新」重新扫描；「打开文件夹」直达当前方案目录。每个方案的角标尺寸/透明度/间距独立保存在该文件夹内的 `badge.json` 中。

## 从源码打包 exe

```powershell
# 安装 PyInstaller
py -3.14 -m pip install --target vendor pyinstaller

# 打包(排除用不到的 Qt 模块以减小体积)
py -3.14 -m PyInstaller --onefile --windowed --name "OBS桌面角标" --icon icon.ico --paths vendor main.py
```

生成的 exe 在 `dist/` 目录。注意：单个 exe 约 48MB（含 Qt 运行库）。

## 项目结构

```
main.py                 程序入口
obs_badge/
  config.py             配置加载/保存(含密码混淆)
  monitor.py            OBS WebSocket 状态监视
  badge_window.py       角标悬浮窗
  settings_window.py    设置窗口
  autostart.py          OBS 启动脚本生成
IconSets/               图标方案
config.example.json     配置示例
install_deps.py         依赖安装
```

## 作者

- 昵称：**四羽Seyyu**
- bilibili：<https://space.bilibili.com/84125742>

## 许可证

本项目采用 [MIT License](LICENSE)。

Copyright (c) 2026 四羽Seyyu
