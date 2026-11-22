zh-hans | [en](https://github.com/Xiaolang47y/Beer/blob/main/README_en.md)

# 🍺 Beer

**B**e **E**mulator mor**E** **R**uined — 一个基于 PyQt6 的 Proton / Wine Windows 程序启动器。

Beer 借用 Steam 下载的 Proton 兼容层（以及系统中已安装的 Wine）来运行 Windows 程序，并提供运行环境检测、Wine 参数调整、Winetricks 组件安装、桌面快捷方式生成等便于启动和管理的工具。

创造此程序的初衷，是为了解决 Wine 在各 Linux 发行版中获取困难、版本管理困难的问题。

> 当前版本：**V1.3**
>
> 此应用使用 TRAE AI 生成，请不放心使用。

干杯！🍺

---

## 功能亮点

| 功能 | 说明 |
| --- | --- |
| Proton / Wine 运行环境表格 | 主页以表格列出名称、类型、版本和路径，自动扫描 Steam 的 Proton 以及系统中的 Wine |
| 自定义运行环境 | 右下角 **添加自定义路径** 可指向 Proton 目录、Wine 目录或 `wine` 可执行文件；**刷新** 重新扫描；**移除** 删除自定义项 |
| Wine 参数设置 | **更多选项** 中可配置 `WINEPREFIX`、Windows 版本、`WINEDLLOVERRIDES`、`WINEDEBUG`、ESYNC / FSYNC、WineD3D、额外 Wine 参数 |
| Winetricks 组件管理 | 独立窗口表格中浏览组件描述、按运行时/前缀安装，内置网络环境提示，并可一键下载 Winetricks |
| 桌面文件生成 | 生成前弹出窗口调整名称、描述、图标、命令参数、`Terminal`、`Categories`、保存位置等，并实时预览与校验 |
| 日志 | 显示完整的进程终端输出，可切换 **自动滚动**，支持保存日志 |
| 已保存应用 | 卡片式管理，支持重命名、切换运行环境、生成桌面快捷方式、打开 Winetricks |
| 啤酒 Emoji 图标 | 应用窗口与快捷方式使用 🍺 图标，缺少 Emoji 字体时自动回退到内置矢量啤酒杯 |
| 双语界面 | 简体中文 / English |

---

## 安装与依赖

### Linux

- Python 3.9 或更高版本
- PyQt6
- 推荐安装 `pefile` 与 `Pillow`，用于从 Windows EXE 中提取图标
- 可选：`winetricks`（也可以在 Beer 的 Winetricks 窗口中一键下载）

```bash
# Debian / Ubuntu
sudo apt install python3 python3-pip python3-venv

# Arch
sudo pacman -S python python-pip

# 安装 Python 依赖（建议使用虚拟环境）
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

如果系统没有彩色 Emoji 字体，窗口图标会使用内置的 `assets/beer.svg` 回退图标；想要彩色 🍺 可以安装：

```bash
# Debian / Ubuntu
sudo apt install fonts-noto-color-emoji
```

### macOS

Beer 的界面可以运行在 macOS 上，但请注意：

- **Proton 只能在 Linux 上运行**，macOS 用户请使用 Wine。
- `.desktop` 文件是 Linux 桌面规范，macOS 不支持，请使用 `.command` 脚本、Automator 应用或 `.app` 包（见下方“macOS 使用方式”）。
- 需要 Python 3.9+ 与 PyQt6。建议使用 Homebrew 安装 Python：

```bash
brew install python
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

---

## 启动此应用

### 方式一：源码运行（Linux / macOS）

```bash
git clone https://github.com/Xiaolang47y/Beer.git
cd Beer
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
bash beer.sh
```

或者直接：

```bash
python3 main.py
```

> 以源码方式运行时，配置文件保存在项目根目录；打包为可执行文件后，配置文件保存在 `~/.config/Beer/`。

### 方式二：下载可执行文件

在 Release 页面下载 `Beer` 可执行文件，赋予执行权限后双击或运行：

```bash
chmod +x Beer
./Beer
```

### 方式三：AppImage（Linux）

```bash
chmod +x Beer-V1.3-x86_64.AppImage
./Beer-V1.3-x86_64.AppImage
```

如果系统没有 FUSE，请安装 `libfuse2`，或使用：

```bash
APPIMAGE_EXTRACT_AND_RUN=1 ./Beer-V1.3-x86_64.AppImage
```

---

## 使用指南

### 1. 准备 Proton

1. 安装 Steam。
2. 在 **库** 页面右上角的筛选中勾选 **工具**。
3. 搜索 Proton，选择版本并安装。
4. 回到 Beer 主页点击 **刷新**，已安装的 Proton 会出现在运行环境表格中。

第三方 Proton（Proton-GE、Wine-GE、Proton-CachyOS 等）可以在 **设置 → 下载 Proton / Wine** 中打开官方下载页。下载并解压后，在主页点击 **添加自定义路径**，选择解压目录即可。

### 2. 主页运行程序

1. 在运行环境表格中选择 Proton 或 Wine。
2. 选择要启动的 `.exe`，并设置运行目录与应用名。
3. 选择架构（32 位 / 64 位 / 自动）。
4. 需要时打开 **更多选项** 调整启动参数与 Wine 参数。
5. 点击 **运行**。

**更多选项** 中还可以设置：

- 启动参数（会传给 Windows 程序）
- `WINEPREFIX`、Windows 版本
- `WINEDLLOVERRIDES`、`WINEDEBUG`
- ESYNC / FSYNC、WineD3D
- 额外 Wine 参数
- 预启动脚本
- 批量启动与启动间隔

### 3. 保存应用与已保存应用页面

- 点击 **保存配置** 保存当前程序配置。
- 在 **已保存应用** 页面双击卡片即可运行。
- 右键卡片可以重命名、切换运行环境、生成桌面快捷方式或打开 Winetricks。

### 4. 日志

**日志** 页面显示进程完整终端输出：

- 勾选 **自动滚动** 时始终定位到最新一行；取消勾选会保留当前滚动位置。
- 自动滚动开关会写入配置，下次启动保持上次选择。
- 可以保存日志到文本文件。

### 5. 生成桌面文件（Linux）

点击 **生成桌面文件** 后会弹出设置窗口，可调整：

- 应用名称与描述（`Name` / `Comment`）
- 可执行文件、工作目录
- 使用的 Proton / Wine 运行环境
- 图标（可选择文件、使用 🍺 Emoji 或从 EXE 提取）
- 命令行参数
- `Categories`
- 是否在终端中打开（`Terminal=true`）
- 保存位置：桌面 / 应用菜单 / 自定义目录
- 文件名

窗口底部会实时预览生成的 `.desktop` 内容，并提示校验错误或警告。生成后会自动设置可执行权限，并尝试写入 `metadata::trusted`。

### 6. Winetricks

在主页右下角点击 **Winetricks** 打开组件管理窗口：

- 顶部会提醒：部分组件需要联网，`.NET`、`vcrun` 等体积较大，某些地区可能需要代理或特殊网络环境。
- 选择目标 Proton / Wine 运行时与 Wine 前缀。
- 在表格中勾选组件（支持搜索、全选、清除）。
- 点击 **安装选中** 开始安装，窗口内会实时显示安装日志。
- 如果系统没有 Winetricks，可点击 **下载 Winetricks**，Beer 会下载官方脚本到 `~/.local/share/Beer/bin/winetricks`。

> 部分组件还需要系统工具，例如 `cabextract`；缺少时 Winetricks 会在日志中提示。

### 7. 配置位置

| 运行方式 | 配置目录 |
| --- | --- |
| 源码运行 | 项目根目录 |
| 可执行文件 / AppImage | `~/.config/Beer/` |

其中 `config.json` 保存设置，`apps.json` 保存已保存的应用。

---

## macOS 使用方式

macOS 无法使用 Proton，但可以使用 Wine：

```bash
# 方式一：Homebrew Wine
brew install --cask wine-stable

# 方式二：Whisky（带图形界面的 Wine 封装）
brew install --cask whisky
```

安装后在 Beer 主页点击 **刷新**，如果 Wine 位于常见路径（如 `/Applications/Wine Stable.app/Contents/Resources/wine/bin/wine`），会自动出现在运行环境表格中；否则使用 **添加自定义路径** 指向 Wine 的 `bin/wine` 或安装目录。

启动 Beer：

```bash
cd Beer
source .venv/bin/activate
python3 main.py
```

如果希望生成 macOS 应用：

```bash
python3 build.py
# PyInstaller 在 macOS 上会生成 dist/Beer.app
open dist/Beer.app
```

由于 macOS 不支持 `.desktop`，可以：

- 创建一个 `.command` 文件（例如 `Beer Game.command`）写入启动命令，并 `chmod +x`；
- 使用 Automator 创建“应用程序”，执行 `open` 或 shell 脚本；
- 或直接使用 PyInstaller 打包 `.app`。

---

## 构建与打包

### 构建单文件可执行程序

```bash
python3 -m pip install -r requirements.txt
python3 build.py
```

输出：`dist/Beer`（Linux）或 `dist/Beer.app`（macOS）。

### 构建 AppImage（Linux）

```bash
python3 build.py --appimage
# 或
bash build_appimage.sh
```

脚本会：

1. 使用 PyInstaller 生成 `dist/Beer`；
2. 创建 AppDir，写入 `AppRun`、`.desktop` 和图标（优先使用 🍺 Emoji 渲染出的 PNG，失败时回退到 `assets/beer.svg`）；
3. 查找或自动下载 `appimagetool`；
4. 输出 `dist/Beer-V1.3-x86_64.AppImage`。

可选环境变量：

```bash
VERSION=1.3 ARCH=x86_64 bash build_appimage.sh
APPIMAGE_EXTRACT_AND_RUN=1 bash build_appimage.sh
APPIMAGETOOL=/path/to/appimagetool bash build_appimage.sh
```

构建 AppImage 需要系统安装 `libfuse2`（运行 AppImage 时也需要）。

---

## 目录结构

```
Beer/
├── main.py                  # 程序入口
├── build.py                 # PyInstaller / AppImage 构建入口
├── build_appimage.sh        # AppImage 打包脚本
├── beer.sh                  # 源码启动脚本
├── assets/beer.svg          # Emoji 不可用时的回退图标
├── packaging/               # AppRun 与 .desktop 模板
├── core/                    # 配置、运行环境检测、Winetricks、桌面文件、图标
├── ui/                      # 主窗口、页面与对话框
└── i18n/translations.py     # 中英文翻译
```

---

## 已知限制

- Proton 仅支持 Linux；macOS 使用 Wine。
- `.desktop` 生成仅适用于 Linux 桌面环境。
- 从 EXE 提取图标需要安装 `pefile` + `Pillow`，或系统提供 `wrest` / `extract-icon`；不可用时会回退到 🍺 Emoji 图标。
- Winetricks 组件下载依赖网络环境，部分组件需要较长时间。
- 自动扫描依赖常见 Steam / Wine 安装路径；非标准路径请使用 **添加自定义路径**。

---

## 画廊

<img width="1366" height="727" alt="截图_2026-11-22_17-24-43" src="https://github.com/user-attachments/assets/edb6a5cf-1a54-4ac7-8709-f415b08ef49f" />
<img width="1366" height="727" alt="截图_2026-11-22_17-21-12" src="https://github.com/user-attachments/assets/9e0cb74a-8cb6-4689-aca3-4552d5cb68b2" />
<img width="1366" height="727" alt="截图_2026-11-22_17-21-20" src="https://github.com/user-attachments/assets/5f2eea8b-3394-4269-acbf-62fbd4dfa2f1" />
<img width="1366" height="727" alt="截图_2026-11-22_17-25-29" src="https://github.com/user-attachments/assets/aa1ca0fd-548f-4eb1-9c92-e3d1fc24d69e" />
<img width="826" height="680" alt="截图_2026-11-22_17-25-08" src="https://github.com/user-attachments/assets/507b8aa8-7335-4fbe-bbf2-59e714e08251" />

---

## 许可证

请参阅 [LICENSE](LICENSE)。
