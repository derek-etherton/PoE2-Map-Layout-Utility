# PoE2 Maps Viewer

A real-time utility for Path of Exile 2 that automatically displays map layouts, optimal flasks, and best weapons based on your current zone and character level. Choose between an overlay mode for single-monitor setups or a windowed mode for dual-monitor setups.

![PoE2 Maps Viewer](https://img.shields.io/badge/Game-Path%20of%20Exile%202-red) ![Python](https://img.shields.io/badge/Python-3.7+-blue) ![License](https://img.shields.io/badge/License-MIT-green)

## 🌟 Features

### 📍 **Zone Detection & Map Display**
- **Real-time zone monitoring** - Automatically detects when you enter a new zone by reading the PoE2 client log file
- **Map overlay** - Displays relevant map layouts in a resizable, always-on-top window
- **Smart folder matching** - Finds maps by matching zone names to your organized map folders

### 🧪 **Flask Optimization**
- **Level-aware flask recommendations** - Shows the best life flask available for your current level
- **Visual flask display** - Displays flask icons, names, level requirements, and healing amounts
- **Regex generation** - One-click copy of flask-specific search filters for in-game use
- **Auto-updating** - Flask recommendations update automatically as you level up

### ⚔️ **Weapon Tracking** 
- **Best-in-slot weapons** - Displays optimal weapons for your selected weapon type and level
- **Detailed stats** - Shows damage, crit chance, attacks per second, and range
- **Multiple weapon types** - Supports Bows, Crossbows, Quarter Staffs, Spears, and Maces
- **Smart updates** - Weapon recommendations refresh when you level up

### 🎮 **User Experience**
- **Borderless overlay** - Clean, minimal interface that doesn't interfere with gameplay
- **System tray integration** - Minimize to tray and control via right-click menu
- **Drag & resize** - Fully customizable window positioning and sizing
- **Level detection** - Automatically detects your character level from game logs
- **Settings persistence** - Remembers your preferences between sessions

## 🚀 Quick Start

### Prerequisites
- Python 3.7+
- Path of Exile 2 installed
- Required Python packages (install via `pip install -r requirements.txt`)

### Installation

1. **Clone or download this repository**
   ```bash
   git clone https://github.com/yourusername/poe-maps.git
   cd poe-maps
   ```

2. **Install dependencies**
   ```bash
   pip install tkinter pillow pystray
   ```

3. **Set up your maps directory**
   - Create a `maps/` folder in the project root
   - Organize by acts: `maps/Act1/`, `maps/Act2/`, etc.
   - Place zone folders inside: `maps/Act1/1_Clearfell/`, `maps/Act1/2_Mud_Burrow/`
   - Add map images (PNG/JPG) to each zone folder

4. **Configure log file path** (if different from default)
   - Open `poe_campaign_layouts.py`
   - Modify line 20: `self.log_file_path = r"your\path\to\Client.txt"`
   - **Note**: Not needed if using executables - configure via Settings window

### Running the Application

**Choose the version that works best for your setup:**

#### 🎯 **Overlay Mode** (Single Monitor)
```bash
python poe_campaign_layouts.py
```
- **Best for**: Single monitor setups
- **Features**: Borderless overlay that renders on top of PoE2
- **Benefits**: System tray integration, always-on-top, minimal interference with gameplay

#### 🪟 **Windowed Mode** (Dual Monitor)
```bash
python poe_campaign_layouts_windowed.py
```
- **Best for**: Dual monitor setups or when you prefer a standalone window
- **Features**: Full-featured windowed application with responsive UI
- **Benefits**: Larger display area, better for detailed map viewing, resizable interface

#### 📦 **Executable Releases** (No Python Required)

Download pre-built executables from the [GitHub Releases](https://github.com/derek-etherton/PoE2-Map-Layout-Utility/releases) page:
- **`PoE_Campaign_Layouts.exe`** - Overlay mode executable
- **`PoE_Campaign_Layouts_Windowed.exe`** - Windowed mode executable

Simply download and run - no Python installation needed!

#### Option 3: Batch File
```bash
./run_viewer.bat
```

## ⚙️ Configuration

### First-Time Setup

**For both versions, you'll need to configure these settings on first launch:**

1. **Set Log Path**:
   - Click "Browse" to locate your PoE2 log file
   - Common locations:
     - `D:\Program Files (x86)\Grinding Gear Games\logs\Client.txt`
     - `~\Documents\My Games\Path of Exile 2\Logs\Client.txt`

2. **Select Weapon Type**:
   - Choose your primary weapon type from the dropdown
   - Options: Bow, Crossbow, Quarter Staff, Spear, One Hand Mace, Two Hand Mace

3. **Set Your Level** (optional):
   - Enter your current character level
   - The app will auto-detect level changes from logs once running

4. **Save Settings**:
   - Click "Save Settings" to persist your configuration
   - Settings are automatically loaded on subsequent launches

### Settings Window

**Overlay Mode**: Access via system tray right-click → Settings
**Windowed Mode**: Expand the "Settings" section in the main window

#### **Regex Filter**
- Custom search pattern for in-game item filtering
- Default: `"increased rar"|move`
- Uses regex syntax - pipe `|` for OR operations

#### **Player Level Override**
- Check "Override player level" to manually set your level
- Useful if auto-detection isn't working
- Leave unchecked to use automatic level detection from game logs

#### **Weapon Base Type**
- Select your primary weapon type from dropdown
- Choose from: Bow, Crossbow, Quarter Staff, Spear, One Hand Mace, Two Hand Mace
- Leave empty to hide weapon tracking

### Directory Structure
```
poe-maps/
├── maps/                    # Your map images organized by act/zone
│   ├── Act1/
│   │   ├── 1_Clearfell/
│   │   │   ├── clearfell_map1.png
│   │   │   └── clearfell_map2.png
│   │   └── 2_Mud_Burrow/
│   └── Act2/
├── images/                  # Flask images
├── public/data/            # Game data files
│   ├── flasks.json
│   └── weapons.json
├── settings.json                    # Your saved preferences
├── poe_campaign_layouts.py          # Overlay mode (single monitor)
├── poe_campaign_layouts_windowed.py # Windowed mode (dual monitor)
├── dist/                            # Pre-built executables
│   ├── PoE_Campaign_Layouts.exe     # Overlay mode executable
│   └── PoE_Campaign_Layouts_Windowed.exe # Windowed mode executable
```

## 🎯 How It Works

### Zone Detection
The application monitors `Client.txt` in your PoE2 logs directory, watching for lines like:
```
[SCENE] Set Source [ZoneName]
```

### Level Detection  
Searches for level-up messages in the format:
```
: PlayerName (ClassName) is now level X
```

### Flask & Weapon Data
- Flask and weapon information stored in JSON files (`public/data/`)
- Automatically finds best items based on level requirements
- Updates display when character levels up

## 🔧 Troubleshooting

### Common Issues

**Maps not showing?**
- Verify your maps folder structure matches zone names
- Check that image files are PNG/JPG format
- Ensure zone detection is working (check console output)

**Level not detecting?**
- Make sure PoE2 is writing to the correct log file location
- Try manually setting level in Settings if auto-detection fails
- Restart the app after changing log file paths

**Flask images not loading?**
- Check that `images/flasks/` directory contains the referenced images
- Fallback colored rectangles will show if images are missing

**Window positioning issues?**
- Use the resize grips in bottom-right corner
- Drag anywhere on the window to reposition
- Settings are remembered between sessions

### Log File Locations
- **Default**: `D:\Program Files (x86)\Grinding Gear Games\logs\Client.txt`
- **Steam**: Usually in the same location, but may vary
- **Custom install**: Update the path in `poe_maps_viewer.py` line 20

## 🛠️ Building Executables

If you want to build the executables yourself, use the provided build scripts:

### Windows Batch Script
```bash
build.bat
```

### PowerShell Script
```powershell
.\build.ps1
```

Both scripts will:
- Check and install PyInstaller if needed
- Clean previous builds
- Build both overlay and windowed mode executables
- Display file sizes and completion status

Executables will be created in the `dist/` folder.

## 🤝 Contributing

Feel free to contribute improvements! Some ideas:
- Add support for more flask types (mana, hybrid)
- Expand weapon database
- Add zone-specific tips or strategies
- Improve map organization tools
- Add automatic map downloads

## 📄 License

This project is open source and available under the MIT License.

## ⚠️ Disclaimer

This tool reads log files only and does not modify game files or memory. It's designed to be a helpful reference overlay, similar to having a browser open on a second monitor. Use responsibly and in accordance with Path of Exile 2's terms of service.

---

*Happy mapping, Exile!* 🗺️⚔️
