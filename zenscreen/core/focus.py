"""
Focus Mode module for ZenScreen.

Provides functionality to block distracting applications and track focus sessions.
"""

import os
import signal
import subprocess
import threading
import time
from datetime import datetime, timedelta
from typing import List, Optional, Callable, Dict, Any
from dataclasses import dataclass, field
import logging

from zenscreen.core.database import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class FocusSession:
    """Represents an active focus session."""
    id: int
    start_time: datetime
    planned_duration: int  # seconds
    blocked_apps: List[str]
    remaining_seconds: int = 0
    is_active: bool = True
    
    @property
    def elapsed_seconds(self) -> int:
        """Get elapsed time in seconds."""
        if not self.is_active:
            return self.planned_duration - self.remaining_seconds
        return int((datetime.now() - self.start_time).total_seconds())
    
    @property
    def progress_percent(self) -> float:
        """Get progress as a percentage (0-100)."""
        if self.planned_duration <= 0:
            return 100.0
        return min(100.0, (self.elapsed_seconds / self.planned_duration) * 100)
    
    @property
    def formatted_remaining(self) -> str:
        """Get formatted remaining time."""
        remaining = max(0, self.planned_duration - self.elapsed_seconds)
        minutes = remaining // 60
        seconds = remaining % 60
        return f"{minutes:02d}:{seconds:02d}"


class AppBlocker:
    """
    Blocks applications by monitoring and closing them.
    
    Note: This is a soft blocker that works by detecting and notifying.
    A hard blocker would require root privileges to modify firewall rules or use cgroups.
    """
    
    def __init__(self):
        self._blocked_apps: List[str] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._on_blocked: Optional[Callable[[str], None]] = None
        self._check_interval = 2.0  # seconds
    
    def set_on_blocked(self, callback: Callable[[str], None]):
        """Set callback for when a blocked app is detected."""
        self._on_blocked = callback
    
    def start_blocking(self, apps: List[str]):
        """Start monitoring and blocking specified apps."""
        self._blocked_apps = [app.lower() for app in apps]
        self._running = True
        self._thread = threading.Thread(target=self._blocking_loop, daemon=True)
        self._thread.start()
        logger.info(f"Started blocking apps: {apps}")
    
    def stop_blocking(self):
        """Stop the blocking loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None
        self._blocked_apps = []
        logger.info("Stopped app blocking")
    
    def _blocking_loop(self):
        """Main loop to check and handle blocked apps."""
        while self._running:
            try:
                blocked = self._check_blocked_apps()
                for app in blocked:
                    if self._on_blocked:
                        self._on_blocked(app)
                    self._notify_blocked(app)
            except Exception as e:
                logger.error(f"Error in blocking loop: {e}")
            
            time.sleep(self._check_interval)
    
    def _check_blocked_apps(self) -> List[str]:
        """Check for running blocked apps."""
        blocked_running = []
        
        try:
            # Get list of running processes
            result = subprocess.run(
                ['ps', '-eo', 'comm'],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0:
                processes = result.stdout.strip().split('\n')
                for proc in processes:
                    proc_lower = proc.lower().strip()
                    for blocked in self._blocked_apps:
                        if blocked in proc_lower:
                            blocked_running.append(proc)
                            break
        except Exception as e:
            logger.error(f"Error checking processes: {e}")
        
        return blocked_running
    
    def _notify_blocked(self, app_name: str):
        """Send a notification about blocked app."""
        try:
            subprocess.run([
                'notify-send',
                '--urgency=critical',
                '--icon=dialog-warning',
                '--app-name=ZenScreen',
                'Focus Mode Active',
                f'"{app_name}" is blocked during your focus session.\nStay focused! 🎯'
            ], timeout=5)
        except Exception as e:
            logger.debug(f"Could not send notification: {e}")
    
    def kill_blocked_apps(self) -> List[str]:
        """Forcefully close all blocked apps. Returns list of killed apps."""
        killed = []
        
        for app in self._blocked_apps:
            try:
                result = subprocess.run(
                    ['pkill', '-f', app],
                    capture_output=True, timeout=5
                )
                if result.returncode == 0:
                    killed.append(app)
            except Exception as e:
                logger.debug(f"Error killing {app}: {e}")
        
        return killed


class FocusMode:
    """
    Main Focus Mode manager.
    
    Handles focus sessions with optional app blocking, break reminders,
    and session tracking.
    """
    
    # Preset focus durations (in minutes)
    PRESETS = {
        'pomodoro': 25,
        'short': 15,
        'medium': 45,
        'long': 60,
        'deep_work': 90,
    }
    
    # Common distracting apps
    DISTRACTION_PRESETS = {
        'social': ['discord', 'slack', 'telegram', 'signal'],
        'video': ['youtube', 'netflix', 'vlc', 'mpv', 'totem'],
        'browsing': ['firefox', 'chromium', 'chrome', 'brave'],
        'games': ['steam', 'lutris', 'retroarch'],
        'all': ['discord', 'slack', 'telegram', 'youtube', 'firefox', 'chromium', 'steam']
    }
    
    def __init__(self, database: Optional[Database] = None):
        """Initialize Focus Mode."""
        self.db = database or Database()
        self._blocker = AppBlocker()
        self._current_session: Optional[FocusSession] = None
        self._timer_thread: Optional[threading.Thread] = None
        self._running = False
        
        # Callbacks
        self._on_tick: Optional[Callable[[FocusSession], None]] = None
        self._on_complete: Optional[Callable[[FocusSession], None]] = None
        self._on_interrupted: Optional[Callable[[FocusSession], None]] = None
    
    @property
    def is_active(self) -> bool:
        """Check if a focus session is currently active."""
        return self._current_session is not None and self._current_session.is_active
    
    @property
    def current_session(self) -> Optional[FocusSession]:
        """Get the current focus session."""
        return self._current_session
    
    def set_on_tick(self, callback: Callable[[FocusSession], None]):
        """Set callback for timer tick (called every second)."""
        self._on_tick = callback
    
    def set_on_complete(self, callback: Callable[[FocusSession], None]):
        """Set callback for session completion."""
        self._on_complete = callback
    
    def set_on_interrupted(self, callback: Callable[[FocusSession], None]):
        """Set callback for session interruption."""
        self._on_interrupted = callback
    
    def start_session(
        self,
        duration_minutes: int = 25,
        blocked_apps: Optional[List[str]] = None,
        use_preset: Optional[str] = None,
        block_preset: Optional[str] = None
    ) -> FocusSession:
        """
        Start a new focus session.
        
        Args:
            duration_minutes: Session duration in minutes
            blocked_apps: List of app names to block
            use_preset: Use a duration preset ('pomodoro', 'short', 'medium', 'long', 'deep_work')
            block_preset: Use a blocking preset ('social', 'video', 'browsing', 'games', 'all')
        
        Returns:
            The new FocusSession object
        """
        if self.is_active:
            raise RuntimeError("A focus session is already active")
        
        # Apply preset duration if specified
        if use_preset and use_preset in self.PRESETS:
            duration_minutes = self.PRESETS[use_preset]
        
        # Apply blocking preset if specified
        if block_preset and block_preset in self.DISTRACTION_PRESETS:
            preset_apps = self.DISTRACTION_PRESETS[block_preset]
            if blocked_apps:
                blocked_apps = list(set(blocked_apps + preset_apps))
            else:
                blocked_apps = preset_apps
        
        blocked_apps = blocked_apps or []
        duration_seconds = duration_minutes * 60
        
        # Create database record
        session_id = self.db.start_focus_session(duration_minutes, blocked_apps)
        
        # Create session object
        self._current_session = FocusSession(
            id=session_id,
            start_time=datetime.now(),
            planned_duration=duration_seconds,
            blocked_apps=blocked_apps,
            remaining_seconds=duration_seconds
        )
        
        # Start app blocker if apps specified
        if blocked_apps:
            self._blocker.start_blocking(blocked_apps)
        
        # Start timer thread
        self._running = True
        self._timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
        self._timer_thread.start()
        
        # Send start notification
        self._send_notification(
            "Focus Session Started",
            f"Stay focused for {duration_minutes} minutes! 🎯"
        )
        
        logger.info(f"Started focus session: {duration_minutes}m, blocking: {blocked_apps}")
        
        return self._current_session
    
    def stop_session(self, completed: bool = False) -> Optional[FocusSession]:
        """
        Stop the current focus session.
        
        Args:
            completed: Whether the session completed naturally (vs interrupted)
        
        Returns:
            The ended FocusSession or None if no active session
        """
        if not self._current_session:
            return None
        
        self._running = False
        
        # Stop blocker
        self._blocker.stop_blocking()
        
        # Update session
        self._current_session.is_active = False
        
        # Update database
        self.db.end_focus_session(self._current_session.id, completed=completed)
        
        # Callbacks
        if completed:
            if self._on_complete:
                self._on_complete(self._current_session)
            self._send_notification(
                "Focus Session Complete! 🎉",
                f"Great job! You stayed focused for {self._current_session.planned_duration // 60} minutes."
            )
        else:
            if self._on_interrupted:
                self._on_interrupted(self._current_session)
            elapsed = self._current_session.elapsed_seconds // 60
            self._send_notification(
                "Focus Session Ended",
                f"Session interrupted after {elapsed} minutes."
            )
        
        session = self._current_session
        self._current_session = None
        
        # Wait for timer thread
        if self._timer_thread:
            self._timer_thread.join(timeout=2.0)
            self._timer_thread = None
        
        logger.info(f"Ended focus session: completed={completed}")
        
        return session
    
    def get_remaining_time(self) -> int:
        """Get remaining time in seconds."""
        if not self._current_session:
            return 0
        
        elapsed = int((datetime.now() - self._current_session.start_time).total_seconds())
        return max(0, self._current_session.planned_duration - elapsed)
    
    def extend_session(self, additional_minutes: int):
        """Extend the current session."""
        if not self._current_session:
            raise RuntimeError("No active focus session")
        
        self._current_session.planned_duration += additional_minutes * 60
        
        self._send_notification(
            "Session Extended",
            f"Added {additional_minutes} more minutes to your focus session."
        )
    
    def get_session_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the current session."""
        if not self._current_session:
            return None
        
        session = self._current_session
        return {
            'id': session.id,
            'start_time': session.start_time.isoformat(),
            'planned_duration_minutes': session.planned_duration // 60,
            'elapsed_seconds': session.elapsed_seconds,
            'remaining_seconds': self.get_remaining_time(),
            'progress_percent': session.progress_percent,
            'formatted_remaining': session.formatted_remaining,
            'blocked_apps': session.blocked_apps,
            'is_active': session.is_active
        }
    
    def _timer_loop(self):
        """Timer loop that runs during focus session."""
        while self._running and self._current_session:
            remaining = self.get_remaining_time()
            self._current_session.remaining_seconds = remaining
            
            # Callback for tick
            if self._on_tick:
                self._on_tick(self._current_session)
            
            # Check if session complete
            if remaining <= 0:
                self.stop_session(completed=True)
                break
            
            # Milestone notifications
            if remaining == 300:  # 5 minutes left
                self._send_notification(
                    "5 Minutes Remaining",
                    "Almost there! Keep going! 💪"
                )
            elif remaining == 60:  # 1 minute left
                self._send_notification(
                    "1 Minute Remaining",
                    "Final stretch! 🏁"
                )
            
            time.sleep(1)
    
    def _send_notification(self, title: str, message: str):
        """Send a desktop notification."""
        try:
            subprocess.run([
                'notify-send',
                '--urgency=normal',
                '--icon=preferences-system-time',
                '--app-name=ZenScreen',
                title,
                message
            ], timeout=5)
        except Exception as e:
            logger.debug(f"Could not send notification: {e}")
    
    # =========== Quick Access Methods ===========
    
    def start_pomodoro(self, blocked_apps: Optional[List[str]] = None) -> FocusSession:
        """Start a 25-minute Pomodoro session."""
        return self.start_session(
            duration_minutes=25,
            blocked_apps=blocked_apps,
            use_preset='pomodoro'
        )
    
    def start_deep_work(self, blocked_apps: Optional[List[str]] = None) -> FocusSession:
        """Start a 90-minute deep work session."""
        apps = blocked_apps or self.DISTRACTION_PRESETS['all']
        return self.start_session(
            duration_minutes=90,
            blocked_apps=apps
        )
    
    def quick_focus(self, minutes: int = 15) -> FocusSession:
        """Start a quick focus session without blocking."""
        return self.start_session(duration_minutes=minutes)


# Test
if __name__ == "__main__":
    focus = FocusMode()
    
    def on_tick(session: FocusSession):
        print(f"\r⏱️  {session.formatted_remaining} remaining ({session.progress_percent:.1f}%)", end='', flush=True)
    
    def on_complete(session: FocusSession):
        print("\n✨ Session complete!")
    
    focus.set_on_tick(on_tick)
    focus.set_on_complete(on_complete)
    
    print("Starting 2-minute focus session...")
    session = focus.start_session(duration_minutes=2, blocked_apps=['discord'])
    
    try:
        while focus.is_active:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        focus.stop_session(completed=False)
