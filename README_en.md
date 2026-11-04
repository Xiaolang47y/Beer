[zh-hans](https://github.com/Xiaolang47y/Beer/blob/main/README.md) | en

# 🍺 Beer

**B**e **E**mulator mor**E** **R**uined — a PyQt6 GUI frontend for running Windows programs with Proton or Wine.

Beer uses the Proton compatibility layer installed through Steam (as well as any system-wide Wine installation) to run Windows programs. It provides runtime detection, Wine parameter tuning, Winetricks component installation, desktop shortcut generation and other tools for launching and managing games and applications.

The original goal of this project was to solve the difficulty of obtaining and managing Wine across Linux distributions.

> Current version: **V1.2**
>
> This application was generated with TRAE AI.

Cheers! 🍺

---

## Features

| Feature | Description |
| --- | --- |
| Proton / Wine runtime table | The main page lists name, type, version and path. Proton installations from Steam and system Wine installations are detected automatically |
| Custom runtimes | **Add Custom Path** accepts a Proton directory, a Wine directory or a `wine` executable; **Refresh** rescans; **Remove** deletes custom entries |
| Wine parameters | **More Options** configures `WINEPREFIX`, Windows version, `WINEDLLOVERRIDES`, `WINEDEBUG`, ESYNC / FSYNC, WineD3D and extra Wine arguments |
| Winetricks manager | A dedicated table with component descriptions, per-runtime/per-prefix installation, a network warning and a one-click Winetricks download |
| Desktop file generation | A dialog lets you adjust name, comment, icon, arguments, `Terminal`, `Categories` and output location, with live preview and validation |
| Logging | Full terminal output, an **Auto-scroll** toggle and saving the log to a file |
| Saved applications | Card-based management with renaming, runtime switching, desktop shortcuts and Winetricks |
| Beer emoji icon | The window and shortcuts use the 🍺 emoji, with a bundled vector beer mug as fallback |
| Bilingual UI | English / Simplified Chinese |

---

## Installation

### Linux

- Python 3.9 or newer
- PyQt6
- Recommended: `pefile` and `Pillow` for icon extraction from Windows EXEs
- Optional: `winetricks` (Beer can also download it from the Winetricks window)

```bash
# Debian / Ubuntu
sudo apt install python3 python3-pip python3-venv

# Arch
sudo pacman -S python python-pip

# Python dependencies (a virtual environment is recommended)
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

If your system has no color emoji font, the window icon falls back to the bundled `assets/beer.svg`. To get the color 🍺 icon:

```bash
# Debian / Ubuntu
sudo apt install fonts-noto-color-emoji
```

### macOS

Beer's interface runs on macOS, but note:

- **Proton is Linux-only**. Use Wine on macOS.
- `.desktop` files are a Linux desktop standard. On macOS use a `.command` script, an Automator app or an `.app` bundle (see “macOS usage” below).
- Python 3.9+ and PyQt6 are required. Homebrew Python is recommended:

```bash
brew install python
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

---

## Launching Beer

### Option 1: Run from source (Linux / macOS)

```bash
git clone https://github.com/Xiaolang47y/Beer.git
cd Beer
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
bash beer.sh
```

Or directly:

```bash
python3 main.py
```

> When running from source, configuration is stored in the project root. When packaged as an executable, configuration is stored in `~/.config/Beer/`.

### Option 2: Download the executable

Download `Beer` from the Releases page, then run:

```bash
chmod +x Beer
./Beer
```

### Option 3: AppImage (Linux)

```bash
chmod +x Beer-V1.2-x86_64.AppImage
./Beer-V1.2-x86_64.AppImage
```

If FUSE is unavailable, install `libfuse2` or run:

```bash
APPIMAGE_EXTRACT_AND_RUN=1 ./Beer-V1.2-x86_64.AppImage
```

---

## Usage

### 1. Install Proton

1. Install Steam.
2. On the **Library** page, enable the **Tools** filter.
3. Search for Proton, choose a version and install it.
4. Open Beer and press **Refresh**. Installed Proton versions appear in the runtime table.

Third-party Proton builds (Proton-GE, Wine-GE, Proton-CachyOS, etc.) are linked from **Settings → Download Proton / Wine**. Extract the archive and use **Add Custom Path** on the main page to select the extracted directory.

### 2. Run a program from the main page

1. Select a Proton or Wine runtime in the table.
2. Choose the `.exe` file and set the working directory and application name.
3. Choose the architecture (32-bit / 64-bit / auto).
4. Optionally open **More Options** to adjust launch and Wine parameters.
5. Press **Run**.

**More Options** also supports:

- Startup arguments passed to the Windows program
- `WINEPREFIX` and Windows version
- `WINEDLLOVERRIDES` and `WINEDEBUG`
- ESYNC / FSYNC and WineD3D
- Extra Wine arguments
- A pre-launch script
- Batch launching with a launch interval

### 3. Saved applications

- Press **Save Config** to save the current program configuration.
- On the **Saved Apps** page, double-click a card to launch it.
- Right-click a card to rename it, switch its runtime, generate a desktop shortcut or open Winetricks.

### 4. Logs

The **Log** page shows the full terminal output:

- With **Auto-scroll** enabled, the view follows the newest line. When disabled, the current scroll position is preserved.
- The toggle is persisted in the configuration.
- The log can be saved to a text file.

### 5. Desktop files (Linux)

Pressing **Generate Desktop File** opens a settings dialog where you can adjust:

- Application name and description (`Name` / `Comment`)
- Executable and working directory
- Proton / Wine runtime
- Icon (choose a file, use the 🍺 emoji or extract it from the EXE)
- Command-line arguments
- `Categories`
- Whether to open in a terminal (`Terminal=true`)
- Destination: Desktop / application menu / custom directory
- File name

The dialog shows a live preview of the resulting `.desktop` file and reports validation errors or warnings. The generated file is made executable and Beer tries to set `metadata::trusted`.

### 6. Winetricks

Press **Winetricks** at the bottom right of the main page:

- The top banner warns that some components need Internet access. Packages such as `.NET` and `vcrun` are large and may take a long time or require a proxy in some regions.
- Select the target Proton / Wine runtime and Wine prefix.
- Tick components in the table (search, Select All and Clear Selection are supported).
- Press **Install Selected**; the installation log is streamed into the window.
- If Winetricks is missing, press **Download Winetricks**. Beer downloads the official script to `~/.local/share/Beer/bin/winetricks`.

> Some components also need system tools such as `cabextract`. Winetricks reports missing tools in the log.

### 7. Configuration locations

| How Beer runs | Configuration directory |
| --- | --- |
| From source | Project root |
| Executable / AppImage | `~/.config/Beer/` |

`config.json` stores settings and `apps.json` stores saved applications.

---

## macOS usage

macOS cannot run Proton, but it can run Wine:

```bash
# Option 1: Homebrew Wine
brew install --cask wine-stable

# Option 2: Whisky (a Wine wrapper with a GUI)
brew install --cask whisky
```

After installation, press **Refresh** on the main page. If Wine is in a common location (for example `/Applications/Wine Stable.app/Contents/Resources/wine/bin/wine`) it will appear in the runtime table automatically. Otherwise use **Add Custom Path** and point it at Wine's `bin/wine` or installation directory.

Launch Beer:

```bash
cd Beer
source .venv/bin/activate
python3 main.py
```

To build a macOS application:

```bash
python3 build.py
# PyInstaller produces dist/Beer.app on macOS
open dist/Beer.app
```

Because macOS does not support `.desktop` files, you can:

- Create a `.command` file (for example `Beer Game.command`) containing the launch command and `chmod +x` it;
- Use Automator to create an application that runs `open` or a shell script;
- Or use the PyInstaller `.app` bundle directly.

---

## Building and packaging

### Single-file executable

```bash
python3 -m pip install -r requirements.txt
python3 build.py
```

Output: `dist/Beer` (Linux) or `dist/Beer.app` (macOS).

### AppImage (Linux)

```bash
python3 build.py --appimage
# or
bash build_appimage.sh
```

The script:

1. Builds `dist/Beer` with PyInstaller;
2. Creates an AppDir containing `AppRun`, the `.desktop` file and an icon (the PNG rendered from the 🍺 emoji when available, otherwise `assets/beer.svg`);
3. Finds or downloads `appimagetool`;
4. Produces `dist/Beer-V1.2-x86_64.AppImage`.

Optional environment variables:

```bash
VERSION=1.2 ARCH=x86_64 bash build_appimage.sh
APPIMAGE_EXTRACT_AND_RUN=1 bash build_appimage.sh
APPIMAGETOOL=/path/to/appimagetool bash build_appimage.sh
```

Building an AppImage requires `libfuse2` (also required to run it).

---

## Project layout

```
Beer/
├── main.py                  # Entry point
├── build.py                 # PyInstaller / AppImage build entry
├── build_appimage.sh        # AppImage packaging script
├── beer.sh                  # Source launcher
├── assets/beer.svg          # Fallback icon when no emoji font is available
├── packaging/               # AppRun and .desktop templates
├── core/                    # Config, runtime detection, Winetricks, desktop files, icons
├── ui/                      # Main window, pages and dialogs
└── i18n/translations.py     # English and Chinese translations
```

---

## Known limitations

- Proton is Linux-only; macOS uses Wine.
- `.desktop` generation is Linux-only.
- Extracting icons from EXEs requires `pefile` + `Pillow`, or `wrest` / `extract-icon`. Otherwise Beer falls back to the 🍺 emoji icon.
- Winetricks component downloads depend on the network; some components take a long time.
- Automatic detection relies on common Steam / Wine paths. Use **Add Custom Path** for non-standard locations.

---

## Gallery

<img width="900" height="628" alt="image" src="https://github.com/user-attachments/assets/ad14232b-3763-4d42-a763-29b2c853406d" />
<img width="900" height="628" alt="image" src="https://github.com/user-attachments/assets/0d5d8a01-1fd8-49b5-913a-e796e1e20811" />
<img width="900" height="628" alt="image" src="https://github.com/user-attachments/assets/02628007-afba-4082-8521-18028f058853" />
<img width="900" height="628" alt="image" src="https://github.com/user-attachments/assets/4ab608bd-5cc3-4262-83a5-7f6b58777dcc" />
<img width="900" height="628" alt="image" src="https://github.com/user-attachments/assets/bb8dd7a4-9cf4-4152-aa68-a7967645a570" />

---

## License

See [LICENSE](LICENSE).
