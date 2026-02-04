# 🧘 Digital Wellbeing for Linux (ZenScreen)

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![AUR](https://img.shields.io/aur/version/zenscreen)](https://aur.archlinux.org/packages/zenscreen)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![GTK4](https://img.shields.io/badge/GTK-4.0-green.svg)](https://gtk.org/)

A beautiful, modern screen time tracker and digital wellbeing app for Linux. Monitor your app usage, set focus sessions, and build healthier digital habits.

![ZenScreen Dashboard](docs/screenshots/dashboard.png)

## ✨ Features

- 📊 **Screen Time Tracking** - Automatically track time spent in applications
- 🖥️ **Multi-Desktop Support** - Works on X11 and Wayland (GNOME, KDE, Sway, Hyprland)
- 🎯 **Focus Mode** - Block distracting apps and improve productivity
- ⏰ **Break Reminders** - Get notified to take regular breaks
- 📈 **Usage Reports** - View daily, weekly, and monthly statistics
- 🌙 **Dark Mode** - Full support for light and dark system themes
- 💻 **CLI & GUI** - Use the terminal or the beautiful GTK4 interface
- 🔒 **Privacy First** - All data stored locally, no cloud sync

## 📸 Screenshots

<details>
<summary>Click to view screenshots</summary>

### Dashboard
![Dashboard](docs/screenshots/dashboard.png)

### Focus Mode
![Focus Mode](docs/screenshots/focus.png)

### CLI Interface
![CLI](docs/screenshots/cli.png)

</details>

## 🚀 Installation

### Arch Linux (AUR)

```bash
# Using yay
yay -S zenscreen

# Using paru
paru -S zenscreen

# Manual installation
git clone https://aur.archlinux.org/zenscreen.git
cd zenscreen
makepkg -si
```

### From Source

```bash
# Clone the repository
# Clone the repository
git clone https://github.com/Someshwar1006/Digital-Wellbeing-for-Linux.git
cd zenscreen

# Install dependencies (Arch Linux)
sudo pacman -S python python-gobject python-cairo gtk4 libadwaita \
    python-click python-rich python-pynput python-xlib python-dbus \
    python-matplotlib python-appdirs xprintidle libnotify

# Install the package
pip install -e .
```

### Dependencies

| Package | Purpose |
|---------|---------|
| python >= 3.11 | Runtime |
| gtk4, libadwaita | GUI framework |
| python-gobject | GTK bindings |
| python-click, python-rich | CLI interface |
| python-xlib, python-pynput | Window tracking |
| python-dbus | D-Bus integration |
| python-matplotlib | Charts |
| xprintidle | Idle detection |
| libnotify | Desktop notifications |

## 📖 Usage

### GUI Application

Launch the graphical interface:

```bash
zenscreen-gtk
```

### CLI Commands

```bash
# View current status and today's stats
zenscreen status

# View detailed reports
zenscreen report --today
zenscreen report --week
zenscreen report --month

# Focus mode
zenscreen focus start                    # Start 25-minute session
zenscreen focus start --duration 45      # Custom duration
zenscreen focus start --preset pomodoro  # Use preset
zenscreen focus start --block discord    # Block specific apps
zenscreen focus stop                     # Stop session
zenscreen focus status                   # Check status
zenscreen focus history                  # View past sessions

# Configuration
zenscreen config list                    # Show all settings
zenscreen config set idle-threshold 300  # Set idle threshold (5 min)
zenscreen config set daily-goal 480      # Set goal (8 hours)

# Background daemon
zenscreen daemon start --foreground      # Run in foreground
zenscreen daemon status                  # Check if running

# Export data
zenscreen export --format json --days 30 > usage.json
zenscreen export --format csv --days 7 > weekly.csv
```

### Enable Auto-Start

To automatically track usage when you log in:

```bash
# Enable the systemd service
systemctl --user enable --now zenscreen.service

# Check status
systemctl --user status zenscreen.service
```

## ⚙️ Configuration

ZenScreen stores configuration in its database. Configure via CLI or GUI:

| Setting | Default | Description |
|---------|---------|-------------|
| `idle_threshold` | 300 | Seconds before marking as idle (5 min) |
| `break_reminder_interval` | 3600 | Break reminder interval (1 hour) |
| `daily_goal_minutes` | 480 | Daily screen time goal (8 hours) |
| `enable_notifications` | true | Show desktop notifications |
| `theme` | system | Theme: system, light, or dark |
| `track_window_titles` | true | Track window titles (privacy) |

```bash
# Examples
zenscreen config set idle_threshold 600       # 10 minute idle
zenscreen config set daily_goal_minutes 360   # 6 hour goal
zenscreen config set enable_notifications false
```

## 🎯 Focus Mode Presets

| Preset | Duration | Description |
|--------|----------|-------------|
| `pomodoro` | 25 min | Classic Pomodoro technique |
| `short` | 15 min | Quick focus burst |
| `medium` | 45 min | Standard work session |
| `long` | 60 min | Extended focus time |
| `deep_work` | 90 min | Deep work session |

Blocking presets:

| Preset | Apps Blocked |
|--------|--------------|
| `social` | Discord, Slack, Telegram, Signal |
| `video` | YouTube, Netflix, VLC, MPV |
| `browsing` | Firefox, Chromium, Chrome |
| `games` | Steam, Lutris |
| `all` | All of the above |

```bash
# Start Pomodoro with social apps blocked
zenscreen focus start --preset pomodoro --block-preset social
```

## 📁 Data Storage

All data is stored locally in `~/.local/share/zenscreen/`:

```
~/.local/share/zenscreen/
├── zenscreen.db      # SQLite database
├── zenscreen.pid     # Daemon PID file
└── logs/             # Log files
    └── zenscreen.log
```

### Export Your Data

```bash
# Export to JSON
zenscreen export --format json --days 90 > my-data.json

# Export to CSV (for spreadsheets)
zenscreen export --format csv --days 30 > monthly-report.csv
```

### Backup

```bash
# Simple backup
cp ~/.local/share/zenscreen/zenscreen.db ~/backup/
```

## 🛠️ Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/someshwar/zenscreen.git
cd zenscreen

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run CLI
zenscreen --help

# Run GUI
zenscreen-gtk
```

### Project Structure

```
zenscreen/
├── pyproject.toml           # Project configuration
├── PKGBUILD                  # AUR package build
├── zenscreen/                # Main package
│   ├── __init__.py
│   ├── __main__.py          # Entry point
│   ├── core/                # Core functionality
│   │   ├── database.py      # SQLite operations
│   │   ├── tracker.py       # Window tracking
│   │   ├── stats.py         # Statistics
│   │   └── focus.py         # Focus mode
│   ├── cli/                 # CLI interface
│   │   └── main.py
│   ├── gui/                 # GTK4 GUI
│   │   └── main.py
│   └── daemon/              # Background service
│       └── service.py
├── data/                    # Assets
│   ├── zenscreen.desktop
│   └── icons/
├── systemd/                 # Service files
│   └── zenscreen.service
└── tests/                   # Test suite
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=zenscreen --cov-report=html
```

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [GNOME](https://www.gnome.org/) for GTK4 and Libadwaita
- [Rich](https://github.com/Textualize/rich) for beautiful terminal output
- [ActivityWatch](https://activitywatch.net/) for inspiration
- The Linux desktop community

## 📞 Support

- 🐛 [Report a bug](https://github.com/Someshwar1006/Digital-Wellbeing-for-Linux/issues/new?template=bug_report.md)
- 💡 [Request a feature](https://github.com/Someshwar1006/Digital-Wellbeing-for-Linux/issues/new?template=feature_request.md)
- 💬 [Discussions](https://github.com/Someshwar1006/Digital-Wellbeing-for-Linux/discussions)

---

<p align="center">
  Made with 💜 for better digital habits
  <br>
  <sub>Take a break. Touch grass. 🌿</sub>
</p>
