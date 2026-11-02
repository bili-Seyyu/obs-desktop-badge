"""OBS 自动启动脚本生成。

生成的 Lua 脚本在 OBS 加载时启动本程序, 并把 OBS 进程 PID 传给它;
本程序通过 PID 守护检测 OBS 退出, 从而自动关闭。
"""
from __future__ import annotations

import sys
from pathlib import Path

from .config import PROJECT_ROOT

SCRIPT_NAME = "obs_badge_autostart.lua"

LUA_TEMPLATE = """-- OBS桌面角标 自动启动脚本(由软件生成, 请勿手动编辑)
obs = obslua

local ffi = require("ffi")
local bit32 = require("bit")
local NORMAL_PRIORITY_CLASS = 0x00000020
local BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
local PRIORITY_CLASS = {priority_class}
local CREATE_NEW_PROCESS_GROUP = 0x00000200

ffi.cdef [[
typedef struct _STARTUPINFOW { uint32_t cb; void * lpReserved; void * lpDesktop; void * lpTitle; uint32_t dwX; uint32_t dwY; uint32_t dwXSize; uint32_t dwYSize; uint32_t dwXCountChars; uint32_t dwYCountChars; uint32_t dwFillAttribute; uint32_t dwFlags; uint16_t wShowWindow; uint16_t cbReserved2; void * lpReserved2; void ** hStdInput; void ** hStdOutput; void ** hStdError; } STARTUPINFOW, *LPSTARTUPINFOW;
typedef struct _PROCESS_INFORMATION { void ** hProcess; void ** hThread; uint32_t dwProcessId; uint32_t dwThreadId; } PROCESS_INFORMATION, *LPPROCESS_INFORMATION;
uint32_t CreateProcessW(void *, const wchar_t * commandLine, void *, void *, uint32_t, uint32_t, void *, const wchar_t *, LPSTARTUPINFOW, LPPROCESS_INFORMATION);
uint32_t CloseHandle(void **);
uint32_t GetCurrentProcessId(void);
int MultiByteToWideChar(unsigned int CodePage, unsigned int dwFlags, const char* lpMultiByteStr, int cbMultiByte, wchar_t* lpWideCharStr, int cchWideChar);
]]

local function execute(commandLine)
    local si = ffi.new("STARTUPINFOW")
    si.cb = ffi.sizeof(si)
    local pi = ffi.new("PROCESS_INFORMATION")
    local widestr = ffi.new("wchar_t[?]", 2048)
    ffi.C.MultiByteToWideChar(65001, 0, commandLine, #commandLine, widestr, 2048)
    local ok = ffi.C.CreateProcessW(nil, widestr, nil, nil, 0, bit32.bor(PRIORITY_CLASS, CREATE_NEW_PROCESS_GROUP), nil, nil, si, pi) ~= 0
    if ok then
        ffi.C.CloseHandle(pi.hProcess)
        ffi.C.CloseHandle(pi.hThread)
    end
    return ok
end

function script_description()
    return [[OBS 启动时自动运行 OBS桌面角标。]]
end

function script_load(settings)
    local obs_pid = ffi.C.GetCurrentProcessId()
    local StartCommand = [[{start_command}]] .. " --obs-pid " .. tostring(obs_pid)
    obs.script_log(obs.LOG_INFO, "启动 OBS桌面角标: " .. StartCommand)
    local ok = execute(StartCommand)
    obs.script_log(obs.LOG_INFO, "启动结果: " .. tostring(ok))
end
"""


def build_start_command() -> str:
    """返回启动本程序的命令行(含引号)。

    开发模式优先用 pythonw.exe, 避免随 OBS 启动时弹出终端窗口。
    """
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    exe = Path(sys.executable)
    pyw = exe.with_name("pythonw.exe")
    if pyw.is_file():
        return f'"{pyw}" "{PROJECT_ROOT / "main.py"}"'
    return f'"{exe}" "{PROJECT_ROOT / "main.py"}"'


def generate_script(low_priority: bool = True) -> Path:
    """在项目根目录生成 Lua 启动脚本, 返回其路径。"""
    priority = "BELOW_NORMAL_PRIORITY_CLASS" if low_priority else "NORMAL_PRIORITY_CLASS"
    content = LUA_TEMPLATE.replace("{start_command}", build_start_command())
    content = content.replace("{priority_class}", priority)
    path = PROJECT_ROOT / SCRIPT_NAME
    path.write_text(content, encoding="utf-8")
    return path
