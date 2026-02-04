"""
ZenScreen Background Daemon Service.

Runs in the background to track application usage and send notifications.
"""

import sys
import os
import signal
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import argparse

from zenscreen.core.database import Database, get_data_dir
from zenscreen.core.tracker import Tracker, WindowInfo

# Set up logging
LOG_DIR = get_data_dir() / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "zenscreen.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ZenScreenDaemon:
    """Background daemon for ZenScreen tracking."""
    
    def __init__(self):
        """Initialize the daemon."""
        self.db = Database()
        self.tracker = Tracker(poll_interval=1.0)
        
        self._running = False
        self._last_break_reminder = datetime.now()
        self._last_cleanup = datetime.now()
        
        # Load settings
        self._load_settings()
        
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
    
    def _load_settings(self):
        """Load settings from database."""
        self.idle_threshold = int(self.db.get_setting('idle_threshold', '300'))
        self.break_interval = int(self.db.get_setting('break_reminder_interval', '3600'))
        self.notifications_enabled = self.db.get_setting('enable_notifications', 'true') == 'true'
        
        # Update tracker settings
        self.tracker.idle_threshold = self.idle_threshold
    
    def _handle_signal(self, signum, frame):
        """Handle termination signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def start(self):
        """Start the daemon."""
        if self._running:
            logger.warning("Daemon is already running")
            return
        
        logger.info("Starting ZenScreen daemon...")
        
        # Close any stale sessions from previous runs
        stale = self.db.close_stale_sessions()
        if stale:
            logger.info(f"Closed {stale} stale sessions from previous run")
        
        # Set up callbacks
        self.tracker.set_on_window_change(self._on_window_change)
        self.tracker.set_on_idle_change(self._on_idle_change)
        
        # Start tracking
        self._running = True
        self.tracker.start(database=self.db)
        
        logger.info(f"Daemon started (session type: {self.tracker.get_session_type()})")
        
        # Main loop
        self._main_loop()
    
    def stop(self):
        """Stop the daemon."""
        logger.info("Stopping ZenScreen daemon...")
        
        self._running = False
        self.tracker.stop()
        
        logger.info("Daemon stopped")
    
    def _main_loop(self):
        """Main daemon loop for periodic tasks."""
        while self._running:
            try:
                now = datetime.now()
                
                # Check for break reminders
                if self.notifications_enabled:
                    self._check_break_reminder(now)
                
                # Daily cleanup (run once per day)
                if now.date() != self._last_cleanup.date():
                    self._daily_cleanup()
                    self._last_cleanup = now
                
                # Reload settings periodically
                if now.minute == 0 and now.second < 10:
                    self._load_settings()
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
            
            time.sleep(10)  # Check every 10 seconds
    
    def _on_window_change(self, window: WindowInfo):
        """Handle window change events."""
        logger.debug(f"Window changed: {window.app_name} - {window.window_title[:50]}")
    
    def _on_idle_change(self, is_idle: bool):
        """Handle idle state changes."""
        if is_idle:
            logger.debug("User went idle")
        else:
            logger.debug("User became active")
    
    def _check_break_reminder(self, now: datetime):
        """Check if it's time to send a break reminder."""
        if not self.tracker.is_idle:
            time_since_break = (now - self._last_break_reminder).total_seconds()
            
            if time_since_break >= self.break_interval:
                self._send_break_notification()
                self._last_break_reminder = now
    
    def _send_break_notification(self):
        """Send a break reminder notification."""
        try:
            import subprocess
            
            # Get today's screen time for context
            from zenscreen.core.stats import Stats
            stats = Stats(self.db)
            today = stats.get_today_stats()
            
            message = f"You've been at your screen for a while.\nTotal today: {today.formatted_time}\n\nTake a moment to rest your eyes! 👀"
            
            subprocess.run([
                'notify-send',
                '--urgency=normal',
                '--icon=preferences-desktop-apps-symbolic',
                '--app-name=ZenScreen',
                '☕ Time for a Break!',
                message
            ], timeout=5)
            
            logger.info("Sent break reminder notification")
            
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")
    
    def _daily_cleanup(self):
        """Perform daily cleanup tasks."""
        logger.info("Running daily cleanup...")
        
        try:
            # Clean up old data (keep 90 days)
            deleted = self.db.cleanup_old_data(days_to_keep=90)
            if deleted:
                logger.info(f"Cleaned up {deleted} old records")
            
            # Clean up old log files
            self._cleanup_logs()
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def _cleanup_logs(self):
        """Remove log files older than 30 days."""
        cutoff = datetime.now() - timedelta(days=30)
        
        for log_file in LOG_DIR.glob("*.log.*"):
            try:
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if mtime < cutoff:
                    log_file.unlink()
                    logger.debug(f"Deleted old log file: {log_file}")
            except Exception as e:
                logger.warning(f"Failed to delete log file {log_file}: {e}")


def get_pid_file() -> Path:
    """Get the PID file path."""
    return get_data_dir() / "zenscreen.pid"


def is_running() -> bool:
    """Check if the daemon is already running."""
    pid_file = get_pid_file()
    
    if not pid_file.exists():
        return False
    
    try:
        pid = int(pid_file.read_text().strip())
        
        # Check if process exists
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, ValueError):
        # Process doesn't exist or invalid PID
        pid_file.unlink(missing_ok=True)
        return False


def write_pid():
    """Write the current PID to the PID file."""
    pid_file = get_pid_file()
    pid_file.write_text(str(os.getpid()))


def remove_pid():
    """Remove the PID file."""
    get_pid_file().unlink(missing_ok=True)


def main():
    """Main entry point for the daemon."""
    parser = argparse.ArgumentParser(
        description="ZenScreen Background Daemon",
        prog="zenscreen-daemon"
    )
    
    parser.add_argument(
        'action',
        choices=['start', 'stop', 'status', 'foreground'],
        nargs='?',
        default='foreground',
        help='Action to perform (default: foreground)'
    )
    
    args = parser.parse_args()
    
    if args.action == 'status':
        if is_running():
            pid = get_pid_file().read_text().strip()
            print(f"ZenScreen daemon is running (PID: {pid})")
            return 0
        else:
            print("ZenScreen daemon is not running")
            return 1
    
    elif args.action == 'stop':
        pid_file = get_pid_file()
        if not pid_file.exists():
            print("ZenScreen daemon is not running")
            return 1
        
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, signal.SIGTERM)
            print(f"Sent SIGTERM to daemon (PID: {pid})")
            
            # Wait for process to exit
            for _ in range(10):
                try:
                    os.kill(pid, 0)
                    time.sleep(0.5)
                except ProcessLookupError:
                    break
            
            remove_pid()
            print("Daemon stopped")
            return 0
            
        except Exception as e:
            print(f"Error stopping daemon: {e}")
            return 1
    
    elif args.action in ('start', 'foreground'):
        if is_running():
            print("ZenScreen daemon is already running")
            return 1
        
        # Write PID file
        write_pid()
        
        try:
            daemon = ZenScreenDaemon()
            print("Starting ZenScreen daemon...")
            daemon.start()
        except KeyboardInterrupt:
            print("\nInterrupted")
        except Exception as e:
            logger.exception(f"Daemon error: {e}")
        finally:
            remove_pid()
        
        return 0


if __name__ == "__main__":
    sys.exit(main())
