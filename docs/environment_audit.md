# 环境审计

检查日期：2026-10-11。项目新建于 `D:\ReadingOS`，未覆盖已有目录或修改其他项目。

| 项目              | 实际结果                                  | 决策                                           |
| ----------------- | ----------------------------------------- | ---------------------------------------------- |
| Windows           | Windows 11 家庭版 中文版，10.0.26200，x64 | 面向 Windows x64                               |
| PowerShell        | 7.6.6                                     | 本地开发命令                                   |
| Node.js / npm     | v24.21.0 / 11.19.0                        | 复用已有安装                                   |
| Git               | 2.53.0.windows.2，已有全局作者配置        | 新建本地仓库；无远程地址                       |
| Rust / Cargo      | PATH 和用户 `.cargo/bin` 未发现           | 不安装系统工具链                               |
| Visual Studio C++ | vswhere 已存在，实例查询返回空数组        | Tauri 构建前置条件缺失                         |
| WebView2 Runtime  | 154.0.4258.62                             | 已安装；Electron 使用自带 Chromium             |
| Edge              | 155.0.4283.45                             | 已安装                                         |
| GitHub CLI        | PATH 和标准安装目录未发现                 | 无 CLI 登录可用；未读取凭据                    |
| npm registry      | 用户原配置为 npmmirror                    | 项目安装使用 npm 官方 registry；未修改全局配置 |

## 桌面技术选择

采用 Electron 44.7.0、React、TypeScript、Vite 和 Node 内置 SQLite。Tauri 2 在 Windows 需要 Rust MSVC 和 C++ Build Tools；目前均不可用。Electron 能使用现有 Node 环境构建完整 Windows 安装包，不需要管理员安装编译工具。代价是安装包和运行内存高于 Tauri。

Electron renderer 启用 sandbox、contextIsolation，关闭 nodeIntegration。文件选择由 native dialog 完成。读取电子书只通过已入库的 asset ID。应用运行时不访问外网。最终用户不需要 Node、Rust 或 WebView2。

依据：[Tauri Windows prerequisites](https://v2.tauri.app/start/prerequisites/)、[Electron security](https://www.electronjs.org/docs/latest/tutorial/security)。
