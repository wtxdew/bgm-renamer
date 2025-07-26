
# Bangumi Renamer (bgm-rnr)

A Python tool for automatically organizing and renaming Bangumi (anime) files to match metadata scraper requirements for **Jellyfin** and **Plex**, with support for multiple naming conventions, special content detection, and multi-language compatibility.


## Features

### 🎯 **Core Functionality**
- **Info Extraction**: Parses series titles, fansub groups, formats, and episode ranges from complex folder names.
- **Hard Linking**: Uses hard links to reduce disk space usage.
- **Clean Folder Structure**: Organizes files into season and extras folders automatically.
- **Archiving**: Moves the original folder to an archive location.
- **Multi-Language Support**: Handles common language tags and regional variations.

### 🔧 **Advanced Features**
- **Dry-Run Mode**: Preview all file operations before they are executed.
- **Configurable Logging**: Set logging levels with color-coded console output.
- **Duplicate Detection**: Detects and warns about potential filename collisions.


## Installation
### Clone the repo (or download the `bgm-rnr.py`)

```bash
git clone https://github.com/yourusername/bgm-renamer.git
cd bgm-renamer
```

### Prerequisites
- Python 3.7 or higher
- pip (Python package manager)

### Install Dependencies
```bash
pip install -r requirements.txt
````

## Usage

```bash
# Recommended: run with --dry-run to preview the result
python3 bgm-rnr.py --dry-run --log-level DEBUG "/path/to/test/folder"

# Process a single folder
python3 bgm-rnr.py "/path/to/anime/folder"

# Process multiple folders at once
python3 bgm-rnr.py "/path/to/folder1" "/path/to/folder2" "/path/to/folder3"
```

### Command Line Options

| Option        | Description                                                                  |
| ------------- | ---------------------------------------------------------------------------- |
| `names`       | One or more folder paths to process (required)                               |
| `--dry-run`   | Preview changes without modifying any files                                  |
| `--log-level` | Set logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL). Default: INFO |



## How It Works

### 📥 Input Structure

The tool expects anime folders using common release formats:

```
[Group] Series Name [01-12] [1080p]/
├── [Group] Series Name [01] [1080p].mkv
├── [Group] Series Name [02] [1080p].mkv
├── SPs/
│   ├── [Group] Series Name - NCED1.mkv
│   ├── [Group] Series Name - PV&CM.mkv
│   └── [Group] Series Name - Menu1.png
└── 特典/
    └── [Group] Series Name - MENU.mkv
```

### 📤 Output Structure

After processing, files are organized into a metadata-friendly structure:

```
Series Name/
├── Season 01/
│   ├── Series Name S01E01.mkv
│   ├── Series Name S01E02.mkv
│   └── Series Name S01E01.zh-TW.ass
└── extras/
    ├── NCED1.mkv
    ├── PV&CM.mkv
    └── MENU.mkv
```

## Supported Naming Patterns

### 📺 Episode Formats

* **Bracket Style**: `[01]`, `[23]` → `S01E01`, `S01E23`
* **Standard Style**: `S01E01`, `S2E5` → `S01E01`, `S02E05`
* **Japanese Style**: `第08話`, `第12話` → `S01E08`, `S01E12`

### 📦 Season Detection

* **From Folder Name**: `Season 2`, `第2期` → Season 02
* **From Filename**: `S02E23`, `第2話` → Season 02
* **Priority**:
  `Filename > Folder > Default (Season 01)`

> ℹ️ Season inferred from filenames takes precedence over folder names.

### 🎞️ Special Content Detection

* **Openings/Endings**: `OP`, `ED`, `NCOP`, `NCED`, `OP1`, `ED2`
* **Promos/Ads**: `PV`, `CM`, `PV1`, `CM2`
* **Extras**: `MENU`, `SP`, `OVA`, `OAD`
* **Japanese Terms**: `映像特典`, `特典`, `第十三话ED`
* **Compound Tags**: `PV&CM4`, `NCOP1&2`, `OP&ED`, `CM1&2&3`

### 🌐 Language Code Support

* **Standard Tags**: `JPTC`, `JPSC`, `ENCN`, `ZHCN`, `ENUS`
* **Hyphenated ISO Codes**: `zh-TW`, `zh-HK`, `en-US`, `ja-JP`
* **Extended Codes**: `zh-Hans`, `zh-Hant`


## TODO

* [ ] Support for user-defined config files
* [ ] Enhanced categorization of extra video types
* [ ] Toggle between Jellyfin and Plex output styles


## License
This project is licensed under the GNU General Public License v3.0.
