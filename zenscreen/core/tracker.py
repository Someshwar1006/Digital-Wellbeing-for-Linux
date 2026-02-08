"""
Window/Application Tracker for ZenScreen.

Tracks active window focus on both X11 and Wayland environments.
"""

import os
import time
import logging
import threading
import subprocess
from typing import Optional, Tuple, Callable
from dataclasses import dataclass
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class WindowInfo:
    """Information about the currently active window."""
    app_name: str
    window_title: str
    window_class: str
    pid: Optional[int] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class X11Tracker:
    """Track active windows on X11 using python-xlib."""
    
    def __init__(self):
        self._display = None
        self._root = None
        self._atom_net_active_window = None
        self._atom_net_wm_name = None
        self._atom_net_wm_pid = None
        self._atom_wm_class = None
        self._initialized = False
        
    def _init_display(self):
        """Initialize X11 display connection."""
        if self._initialized:
            return True
            
        try:
            from Xlib import display, X
            from Xlib.protocol import rq
            
            self._display = display.Display()
            self._root = self._display.screen().root
            
            # Get atoms for window properties
            self._atom_net_active_window = self._display.intern_atom('_NET_ACTIVE_WINDOW')
            self._atom_net_wm_name = self._display.intern_atom('_NET_WM_NAME')
            self._atom_net_wm_pid = self._display.intern_atom('_NET_WM_PID')
            self._atom_wm_class = self._display.intern_atom('WM_CLASS')
            self._atom_wm_name = self._display.intern_atom('WM_NAME')
            
            self._initialized = True
            return True
        except Exception as e:
            logger.warning(f"Failed to initialize X11 display: {e}")
            return False
    
    def get_active_window(self) -> Optional[WindowInfo]:
        """Get information about the currently active window."""
        if not self._init_display():
            return None
            
        try:
            from Xlib import X
            
            # Get active window ID
            response = self._root.get_full_property(
                self._atom_net_active_window, X.AnyPropertyType
            )
            
            if not response or not response.value:
                return None
                
            window_id = response.value[0]
            if window_id == 0:
                return None
                
            window = self._display.create_resource_object('window', window_id)
            
            # Get window title (try _NET_WM_NAME first, then WM_NAME)
            window_title = ""
            try:
                name_prop = window.get_full_property(self._atom_net_wm_name, 0)
                if name_prop:
                    window_title = name_prop.value.decode('utf-8', errors='replace')
            except Exception:
                pass
            
            if not window_title:
                try:
                    name_prop = window.get_full_property(self._atom_wm_name, 0)
                    if name_prop:
                        window_title = name_prop.value.decode('latin-1', errors='replace')
                except Exception:
                    pass
            
            # Get WM_CLASS (app name)
            app_name = "Unknown"
            window_class = ""
            try:
                class_prop = window.get_full_property(self._atom_wm_class, 0)
                if class_prop:
                    # WM_CLASS contains two null-terminated strings
                    classes = class_prop.value.decode('utf-8', errors='replace').rstrip('\x00').split('\x00')
                    if len(classes) >= 2:
                        app_name = classes[1]  # Use class name (usually more stable)
                        window_class = classes[0]  # Instance name
                    elif classes:
                        app_name = classes[0]
                        window_class = classes[0]
            except Exception:
                pass
            
            # Get PID
            pid = None
            try:
                pid_prop = window.get_full_property(self._atom_net_wm_pid, 0)
                if pid_prop:
                    pid = pid_prop.value[0]
            except Exception:
                pass
            
            return WindowInfo(
                app_name=app_name,
                window_title=window_title,
                window_class=window_class,
                pid=pid
            )
            
        except Exception as e:
            logger.error(f"Error getting active window: {e}")
            return None


class WaylandTracker:
    """Track active windows on Wayland using external tools."""
    
    def __init__(self):
        self._compositor = self._detect_compositor()
    
    def _detect_compositor(self) -> str:
        """Detect which Wayland compositor is running."""
        desktop = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
        session = os.environ.get('XDG_SESSION_DESKTOP', '').lower()
        
        if 'gnome' in desktop or 'gnome' in session:
            return 'gnome'
        elif 'kde' in desktop or 'kde' in session or 'plasma' in desktop:
            return 'kde'
        elif 'sway' in desktop or 'sway' in session:
            return 'sway'
        elif 'hyprland' in desktop or 'hyprland' in session:
            return 'hyprland'
        else:
            return 'generic'
    
    def get_active_window(self) -> Optional[WindowInfo]:
        """Get active window info using compositor-specific methods."""
        if self._compositor == 'gnome':
            return self._get_gnome_active_window()
        elif self._compositor == 'kde':
            return self._get_kde_active_window()
        elif self._compositor == 'sway':
            return self._get_sway_active_window()
        elif self._compositor == 'hyprland':
            return self._get_hyprland_active_window()
        else:
            return self._get_generic_active_window()
    
    def _get_gnome_active_window(self) -> Optional[WindowInfo]:
        """Get active window on GNOME using multiple methods."""
        
        # Method 1: Try gdbus Eval (works on older GNOME, disabled on GNOME 45+)
        try:
            result = subprocess.run(
                ['gdbus', 'call', '--session', '--dest', 'org.gnome.Shell',
                 '--object-path', '/org/gnome/Shell',
                 '--method', 'org.gnome.Shell.Eval',
                 'global.display.get_focus_window()?.get_wm_class() || ""'],
                capture_output=True, text=True, timeout=2
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                # Check if Eval returned success (true, 'result')
                if output.startswith('(true,'):
                    import re
                    match = re.search(r"'([^']*)'", output)
                    if match and match.group(1):
                        app_name = match.group(1).strip('"')
                        if app_name:
                            return WindowInfo(
                                app_name=app_name,
                                window_title="",
                                window_class=app_name
                            )
        except Exception as e:
            logger.debug(f"GNOME Eval detection failed: {e}")
        
        # Method 2: Scan /proc for GUI applications and use heuristics
        return self._detect_focused_app_from_proc()
    
    def _detect_focused_app_from_proc(self) -> Optional[WindowInfo]:
        """Detect focused app by scanning /proc for known GUI applications."""
        import os
        import glob
        
        # Known GUI applications with their process names
        gui_apps = {
            'chrome': 'Chrome',
            'chromium': 'Chromium',
            'firefox': 'Firefox',
            'firefox-esr': 'Firefox',
            'code': 'VS Code',
            'code-oss': 'VS Code',
            'cursor': 'Cursor',
            'antigravity': 'Antigravity',
            'slack': 'Slack',
            'discord': 'Discord',
            'spotify': 'Spotify',
            'telegram': 'Telegram',
            'thunderbird': 'Thunderbird',
            'nautilus': 'Files',
            'gnome-terminal': 'Terminal',
            'tilix': 'Tilix',
            'alacritty': 'Alacritty',
            'kitty': 'Kitty',
            'obs': 'OBS',
            'gimp': 'GIMP',
            'inkscape': 'Inkscape',
            'blender': 'Blender',
            'steam': 'Steam',
            'vlc': 'VLC',
            'mpv': 'mpv',
            'eog': 'Image Viewer',
            'evince': 'Document Viewer',
            'gedit': 'Text Editor',
            'libreoffice': 'LibreOffice',
            'tradingview': 'TradingView',
            'zenscreen': 'ZenScreen',
        }
        
        # Find running GUI processes
        found_apps = []
        try:
            for pid_dir in glob.glob('/proc/[0-9]*'):
                try:
                    pid = os.path.basename(pid_dir)
                    
                    # Read process command
                    with open(f'{pid_dir}/comm', 'r') as f:
                        comm = f.read().strip().lower()
                    
                    # Read full cmdline for better matching
                    try:
                        with open(f'{pid_dir}/cmdline', 'r') as f:
                            cmdline = f.read().replace('\x00', ' ').lower()
                    except:
                        cmdline = comm
                    
                    # Check against known apps
                    for proc_name, app_name in gui_apps.items():
                        if proc_name in comm or proc_name in cmdline:
                            # Get process start time for recency
                            try:
                                stat = os.stat(pid_dir)
                                found_apps.append((stat.st_mtime, app_name, proc_name))
                            except:
                                found_apps.append((0, app_name, proc_name))
                            break
                except (IOError, OSError):
                    continue
        except Exception as e:
            logger.debug(f"Proc scanning failed: {e}")
        
        # Return the most recently started GUI app (heuristic for focus)
        if found_apps:
            # Sort by start time, most recent first
            found_apps.sort(key=lambda x: x[0], reverse=True)
            # Prefer non-ZenScreen apps
            for _, app_name, proc_name in found_apps:
                if 'zenscreen' not in proc_name.lower():
                    return WindowInfo(
                        app_name=app_name,
                        window_title="",
                        window_class=proc_name
                    )
            # Fallback to first found
            return WindowInfo(
                app_name=found_apps[0][1],
                window_title="",
                window_class=found_apps[0][2]
            )
        
        return self._get_generic_active_window()
    
    def _get_kde_active_window(self) -> Optional[WindowInfo]:
        """Get active window on KDE Plasma using qdbus."""
        try:
            result = subprocess.run(
                ['qdbus', 'org.kde.KWin', '/KWin', 'org.kde.KWin.activeWindow'],
                capture_output=True, text=True, timeout=2
            )
            
            if result.returncode == 0:
                window_id = result.stdout.strip()
                if window_id:
                    # Get window class
                    class_result = subprocess.run(
                        ['qdbus', 'org.kde.KWin', f'/KWin/Window{window_id}',
                         'org.kde.KWin.Window.resourceClass'],
                        capture_output=True, text=True, timeout=2
                    )
                    
                    if class_result.returncode == 0:
                        app_name = class_result.stdout.strip()
                        if app_name:
                            return WindowInfo(
                                app_name=app_name,
                                window_title="",
                                window_class=app_name
                            )
        except Exception as e:
            logger.debug(f"KDE window detection failed: {e}")
        
        return self._get_generic_active_window()
    
    def _get_sway_active_window(self) -> Optional[WindowInfo]:
        """Get active window on Sway using swaymsg."""
        try:
            import json
            result = subprocess.run(
                ['swaymsg', '-t', 'get_tree'],
                capture_output=True, text=True, timeout=2
            )
            
            if result.returncode == 0:
                tree = json.loads(result.stdout)
                focused = self._find_focused_sway(tree)
                if focused:
                    return WindowInfo(
                        app_name=focused.get('app_id', '') or focused.get('window_properties', {}).get('class', 'Unknown'),
                        window_title=focused.get('name', ''),
                        window_class=focused.get('app_id', '')
                    )
        except Exception as e:
            logger.debug(f"Sway window detection failed: {e}")
        
        return None
    
    def _find_focused_sway(self, node: dict) -> Optional[dict]:
        """Recursively find the focused window in Sway's tree."""
        if node.get('focused'):
            return node
        for child in node.get('nodes', []) + node.get('floating_nodes', []):
            result = self._find_focused_sway(child)
            if result:
                return result
        return None
    
    def _get_hyprland_active_window(self) -> Optional[WindowInfo]:
        """Get active window on Hyprland using hyprctl."""
        try:
            import json
            result = subprocess.run(
                ['hyprctl', 'activewindow', '-j'],
                capture_output=True, text=True, timeout=2
            )
            
            if result.returncode == 0 and result.stdout.strip():
                window = json.loads(result.stdout)
                return WindowInfo(
                    app_name=window.get('class', 'Unknown'),
                    window_title=window.get('title', ''),
                    window_class=window.get('class', ''),
                    pid=window.get('pid')
                )
        except Exception as e:
            logger.debug(f"Hyprland window detection failed: {e}")
        
        return None
    
    def _get_generic_active_window(self) -> Optional[WindowInfo]:
        """Fallback method using xdotool if available (XWayland)."""
        try:
            result = subprocess.run(
                ['xdotool', 'getactivewindow', 'getwindowname'],
                capture_output=True, text=True, timeout=2
            )
            
            if result.returncode == 0:
                window_title = result.stdout.strip()
                
                # Try to get window class
                class_result = subprocess.run(
                    ['xdotool', 'getactivewindow', 'getwindowclassname'],
                    capture_output=True, text=True, timeout=2
                )
                
                app_name = class_result.stdout.strip() if class_result.returncode == 0 else "Unknown"
                
                return WindowInfo(
                    app_name=app_name or "Unknown",
                    window_title=window_title,
                    window_class=app_name
                )
        except Exception as e:
            logger.debug(f"xdotool fallback failed: {e}")
        
        return None


class IdleDetector:
    """Detect user idle time."""
    
    def __init__(self):
        self._session_type = os.environ.get('XDG_SESSION_TYPE', 'x11')
    
    def get_idle_time(self) -> int:
        """Get idle time in seconds."""
        if self._session_type == 'wayland':
            return self._get_idle_wayland()
        else:
            return self._get_idle_x11()
    
    def _get_idle_x11(self) -> int:
        """Get idle time on X11 using xprintidle."""
        try:
            result = subprocess.run(
                ['xprintidle'],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                # xprintidle returns milliseconds
                return int(result.stdout.strip()) // 1000
        except Exception as e:
            logger.debug(f"xprintidle failed: {e}")
        
        # Fallback using python-xlib
        try:
            from Xlib import display
            from Xlib.ext import screensaver
            
            d = display.Display()
            info = screensaver.query_info(d.screen().root)
            return info.idle // 1000  # Convert to seconds
        except Exception as e:
            logger.debug(f"Xlib idle detection failed: {e}")
        
        return 0
    
    def _get_idle_wayland(self) -> int:
        """Get idle time on Wayland (compositor-specific)."""
        # Try using dbus for GNOME
        try:
            result = subprocess.run(
                ['dbus-send', '--print-reply', '--dest=org.gnome.Mutter.IdleMonitor',
                 '/org/gnome/Mutter/IdleMonitor/Core',
                 'org.gnome.Mutter.IdleMonitor.GetIdletime'],
                capture_output=True, text=True, timeout=2
            )
            
            if result.returncode == 0:
                # Parse the output to get idle time
                for line in result.stdout.split('\n'):
                    if 'uint64' in line:
                        idle_ms = int(line.split()[-1])
                        return idle_ms // 1000
        except Exception:
            pass
        
        # Try KDE
        try:
            result = subprocess.run(
                ['qdbus', 'org.kde.screensaver', '/ScreenSaver',
                 'org.freedesktop.ScreenSaver.GetSessionIdleTime'],
                capture_output=True, text=True, timeout=2
            )
            
            if result.returncode == 0:
                return int(result.stdout.strip())
        except Exception:
            pass
        
        return 0


class Tracker:
    """Main tracker class that handles window monitoring and data collection."""
    
    def __init__(self, poll_interval: float = 1.0, idle_threshold: int = 300):
        """
        Initialize the tracker.
        
        Args:
            poll_interval: How often to check the active window (seconds)
            idle_threshold: Time before considering user idle (seconds)
        """
        self.poll_interval = poll_interval
        self.idle_threshold = idle_threshold
        
        self._session_type = os.environ.get('XDG_SESSION_TYPE', 'x11')
        
        # Initialize the appropriate tracker
        if self._session_type == 'wayland':
            self._window_tracker = WaylandTracker()
        else:
            self._window_tracker = X11Tracker()
        
        self._idle_detector = IdleDetector()
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._current_window: Optional[WindowInfo] = None
        self._current_session_id: Optional[int] = None
        self._is_idle = False
        
        # Callbacks
        self._on_window_change: Optional[Callable[[WindowInfo], None]] = None
        self._on_idle_change: Optional[Callable[[bool], None]] = None
        
        # Suspend detection - if time between polls > 5 min, system was likely suspended
        self._last_poll_time: Optional[float] = None
        self._suspend_threshold = 300  # 5 minutes in seconds
    
    @property
    def is_running(self) -> bool:
        """Check if the tracker is currently running."""
        return self._running
    
    @property
    def current_window(self) -> Optional[WindowInfo]:
        """Get the current active window info."""
        return self._current_window
    
    @property
    def is_idle(self) -> bool:
        """Check if the user is currently idle."""
        return self._is_idle
    
    def set_on_window_change(self, callback: Callable[[WindowInfo], None]):
        """Set callback for window change events."""
        self._on_window_change = callback
    
    def set_on_idle_change(self, callback: Callable[[bool], None]):
        """Set callback for idle state changes."""
        self._on_idle_change = callback
    
    def get_active_window(self) -> Optional[WindowInfo]:
        """Get the currently active window."""
        return self._window_tracker.get_active_window()
    
    def get_idle_time(self) -> int:
        """Get current idle time in seconds."""
        return self._idle_detector.get_idle_time()
    
    def start(self, database=None):
        """Start the tracking loop."""
        if self._running:
            logger.warning("Tracker is already running")
            return
        
        self._running = True
        self._database = database
        self._thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self._thread.start()
        logger.info("Tracker started")
    
    def stop(self):
        """Stop the tracking loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None
        
        # Close current session
        if self._current_session_id and self._database:
            self._database.end_app_session(self._current_session_id)
            self._current_session_id = None
        
        logger.info("Tracker stopped")
    
    def _tracking_loop(self):
        """Main tracking loop."""
        while self._running:
            try:
                current_time = time.time()
                
                # Detect suspend/sleep - if time gap is too large, close current session
                if self._last_poll_time is not None:
                    time_gap = current_time - self._last_poll_time
                    if time_gap > self._suspend_threshold:
                        logger.info(f"Detected suspend/sleep (gap: {time_gap:.0f}s), closing current session")
                        if self._current_session_id and self._database:
                            # Close the session at the time we last polled (before suspend)
                            self._database.end_app_session(self._current_session_id)
                            self._current_session_id = None
                            self._current_window = None
                
                self._last_poll_time = current_time
                
                # Check idle state
                idle_time = self.get_idle_time()
                was_idle = self._is_idle
                self._is_idle = idle_time >= self.idle_threshold
                
                if was_idle != self._is_idle and self._on_idle_change:
                    self._on_idle_change(self._is_idle)
                
                # Get active window
                if not self._is_idle:
                    new_window = self.get_active_window()
                    
                    if new_window:
                        # Check if window changed
                        window_changed = (
                            self._current_window is None or
                            self._current_window.app_name != new_window.app_name or
                            self._current_window.window_title != new_window.window_title
                        )
                        
                        if window_changed:
                            # End previous session
                            if self._current_session_id and self._database:
                                self._database.end_app_session(self._current_session_id)
                            
                            # Start new session
                            if self._database:
                                self._current_session_id = self._database.start_app_session(
                                    new_window.app_name,
                                    new_window.window_title
                                )
                            
                            self._current_window = new_window
                            
                            if self._on_window_change:
                                self._on_window_change(new_window)
                            
                            logger.debug(f"Window changed: {new_window.app_name} - {new_window.window_title}")
                else:
                    # User is idle, close current session
                    if self._current_session_id and self._database:
                        self._database.end_app_session(self._current_session_id)
                        self._current_session_id = None
                        self._current_window = None
                
            except Exception as e:
                logger.error(f"Error in tracking loop: {e}")
            
            time.sleep(self.poll_interval)
    
    def get_session_type(self) -> str:
        """Get the current session type (x11 or wayland)."""
        return self._session_type


# Simple test
if __name__ == "__main__":
    import time
    
    tracker = Tracker(poll_interval=1.0, idle_threshold=30)
    
    def on_window_change(window: WindowInfo):
        print(f"Window changed: {window.app_name} - {window.window_title[:50]}...")
    
    def on_idle_change(is_idle: bool):
        print(f"Idle state changed: {'idle' if is_idle else 'active'}")
    
    tracker.set_on_window_change(on_window_change)
    tracker.set_on_idle_change(on_idle_change)
    
    print(f"Session type: {tracker.get_session_type()}")
    print("Starting tracker... Press Ctrl+C to stop")
    
    tracker.start()
    
    try:
        while True:
            window = tracker.current_window
            if window:
                print(f"Current: {window.app_name} | Idle: {tracker.is_idle}")
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nStopping...")
        tracker.stop()
