"""
Statistics module for ZenScreen.

Provides data analysis and reporting functionality.
"""

from datetime import date, datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import json

from zenscreen.core.database import Database


@dataclass
class UsageStats:
    """Container for usage statistics."""
    total_screen_time: int  # seconds
    active_time: int  # seconds
    idle_time: int  # seconds
    app_breakdown: List[Dict[str, Any]]
    session_count: int
    unique_apps: int
    first_activity: Optional[str] = None
    last_activity: Optional[str] = None
    
    @property
    def total_hours(self) -> float:
        """Get total screen time in hours."""
        return self.total_screen_time / 3600
    
    @property
    def formatted_time(self) -> str:
        """Get formatted total screen time (e.g., '3h 24m')."""
        hours = self.total_screen_time // 3600
        minutes = (self.total_screen_time % 3600) // 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"


@dataclass
class WeeklyStats:
    """Container for weekly statistics."""
    days: List[Dict[str, Any]]
    total_screen_time: int
    daily_average: int
    most_used_apps: List[Dict[str, Any]]
    busiest_day: Optional[str] = None
    trend: str = "stable"  # "up", "down", "stable"


@dataclass
class FocusStats:
    """Container for focus session statistics."""
    total_sessions: int
    completed_sessions: int
    total_focus_time: int  # seconds
    average_session_length: int  # seconds
    completion_rate: float  # 0-100


class Stats:
    """Statistics calculator for ZenScreen data."""
    
    def __init__(self, database: Optional[Database] = None):
        """Initialize with a database connection."""
        self.db = database or Database()
    
    def get_today_stats(self) -> UsageStats:
        """Get usage statistics for today."""
        return self.get_day_stats(date.today())
    
    def get_day_stats(self, target_date: date) -> UsageStats:
        """Get usage statistics for a specific day."""
        app_summary = self.db.get_app_usage_summary(target_date)
        usage_records = self.db.get_usage_for_date(target_date)
        
        total_time = sum(app['total_duration'] for app in app_summary)
        session_count = sum(app['session_count'] for app in app_summary)
        
        # Calculate percentages for each app
        for app in app_summary:
            if total_time > 0:
                app['percentage'] = round((app['total_duration'] / total_time) * 100, 1)
            else:
                app['percentage'] = 0
            
            # Format duration
            app['formatted_duration'] = self._format_duration(app['total_duration'])
        
        # Get first and last activity times
        first_activity = None
        last_activity = None
        
        if usage_records:
            first_activity = usage_records[0].get('start_time')
            for record in reversed(usage_records):
                if record.get('end_time'):
                    last_activity = record['end_time']
                    break
        
        return UsageStats(
            total_screen_time=total_time,
            active_time=total_time,  # For now, same as total
            idle_time=0,  # Would need separate tracking
            app_breakdown=app_summary,
            session_count=session_count,
            unique_apps=len(app_summary),
            first_activity=first_activity,
            last_activity=last_activity
        )
    
    def get_week_stats(self, end_date: Optional[date] = None) -> WeeklyStats:
        """Get usage statistics for the past 7 days."""
        if end_date is None:
            end_date = date.today()
        
        weekly_data = self.db.get_weekly_summary(end_date)
        
        total_time = sum(day['total_duration'] for day in weekly_data)
        days_with_data = sum(1 for day in weekly_data if day['total_duration'] > 0)
        daily_average = total_time // days_with_data if days_with_data > 0 else 0
        
        # Find busiest day
        busiest_day = None
        max_time = 0
        for day in weekly_data:
            if day['total_duration'] > max_time:
                max_time = day['total_duration']
                busiest_day = day['date']
        
        # Format days
        for day in weekly_data:
            day['formatted_duration'] = self._format_duration(day['total_duration'])
            day['day_name'] = self._get_day_name(day['date'])
        
        # Calculate trend (compare last 3 days to previous 4)
        if len(weekly_data) >= 7:
            recent = sum(d['total_duration'] for d in weekly_data[-3:])
            previous = sum(d['total_duration'] for d in weekly_data[:4])
            
            recent_avg = recent / 3
            previous_avg = previous / 4
            
            if recent_avg > previous_avg * 1.2:
                trend = "up"
            elif recent_avg < previous_avg * 0.8:
                trend = "down"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        # Get most used apps for the week
        start_date = end_date - timedelta(days=6)
        most_used = self._get_top_apps_range(start_date, end_date, limit=5)
        
        return WeeklyStats(
            days=weekly_data,
            total_screen_time=total_time,
            daily_average=daily_average,
            most_used_apps=most_used,
            busiest_day=busiest_day,
            trend=trend
        )
    
    def get_month_stats(self, year: int = None, month: int = None) -> Dict[str, Any]:
        """Get usage statistics for a month."""
        if year is None or month is None:
            today = date.today()
            year = today.year
            month = today.month
        
        return self.db.get_monthly_summary(year, month)
    
    def get_focus_stats(self, days: int = 30) -> FocusStats:
        """Get focus session statistics."""
        history = self.db.get_focus_history(days)
        
        if not history:
            return FocusStats(
                total_sessions=0,
                completed_sessions=0,
                total_focus_time=0,
                average_session_length=0,
                completion_rate=0.0
            )
        
        total = len(history)
        completed = sum(1 for s in history if s.get('completed'))
        total_time = sum(s.get('actual_duration', 0) for s in history)
        avg_length = total_time // total if total > 0 else 0
        completion_rate = (completed / total * 100) if total > 0 else 0.0
        
        return FocusStats(
            total_sessions=total,
            completed_sessions=completed,
            total_focus_time=total_time,
            average_session_length=avg_length,
            completion_rate=round(completion_rate, 1)
        )
    
    def get_app_history(self, app_name: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get usage history for a specific app."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)
        
        history = []
        current = start_date
        
        while current <= end_date:
            summary = self.db.get_app_usage_summary(current)
            app_data = next((a for a in summary if a['app_name'] == app_name), None)
            
            history.append({
                'date': current.isoformat(),
                'duration': app_data['total_duration'] if app_data else 0,
                'sessions': app_data['session_count'] if app_data else 0
            })
            
            current += timedelta(days=1)
        
        return history
    
    def get_productivity_score(self, target_date: date = None) -> Dict[str, Any]:
        """
        Calculate a productivity score based on app usage patterns.
        
        This is a simple heuristic based on categorized apps.
        Productivity score = (productive_time / total_time) * 100
        """
        if target_date is None:
            target_date = date.today()
        
        stats = self.get_day_stats(target_date)
        
        # Define productive and unproductive app patterns
        productive_patterns = [
            'code', 'vscode', 'vim', 'emacs', 'sublime', 'atom', 'idea', 'pycharm',
            'terminal', 'konsole', 'gnome-terminal', 'alacritty', 'kitty',
            'libreoffice', 'gimp', 'inkscape', 'blender', 'krita',
            'notion', 'obsidian', 'logseq', 'joplin',
            'thunderbird', 'evolution', 'geary'
        ]
        
        unproductive_patterns = [
            'youtube', 'netflix', 'twitch', 'reddit', 'twitter', 'facebook',
            'instagram', 'tiktok', 'discord', 'slack', 'telegram',
            'steam', 'lutris', 'game'
        ]
        
        productive_time = 0
        unproductive_time = 0
        neutral_time = 0
        
        for app in stats.app_breakdown:
            app_name_lower = app['app_name'].lower()
            duration = app['total_duration']
            
            is_productive = any(p in app_name_lower for p in productive_patterns)
            is_unproductive = any(p in app_name_lower for p in unproductive_patterns)
            
            if is_productive:
                productive_time += duration
            elif is_unproductive:
                unproductive_time += duration
            else:
                neutral_time += duration
        
        total = stats.total_screen_time
        
        if total > 0:
            score = ((productive_time + neutral_time * 0.5) / total) * 100
        else:
            score = 0
        
        return {
            'score': round(min(100, score), 1),
            'productive_time': productive_time,
            'unproductive_time': unproductive_time,
            'neutral_time': neutral_time,
            'productive_formatted': self._format_duration(productive_time),
            'unproductive_formatted': self._format_duration(unproductive_time),
            'recommendation': self._get_productivity_recommendation(score)
        }
    
    def get_usage_comparison(self, date1: date, date2: date) -> Dict[str, Any]:
        """Compare usage between two dates."""
        stats1 = self.get_day_stats(date1)
        stats2 = self.get_day_stats(date2)
        
        time_diff = stats2.total_screen_time - stats1.total_screen_time
        time_diff_pct = (time_diff / stats1.total_screen_time * 100) if stats1.total_screen_time > 0 else 0
        
        return {
            'date1': {
                'date': date1.isoformat(),
                'total_time': stats1.total_screen_time,
                'formatted': stats1.formatted_time,
                'apps': stats1.unique_apps
            },
            'date2': {
                'date': date2.isoformat(),
                'total_time': stats2.total_screen_time,
                'formatted': stats2.formatted_time,
                'apps': stats2.unique_apps
            },
            'difference': {
                'seconds': time_diff,
                'percentage': round(time_diff_pct, 1),
                'formatted': self._format_duration(abs(time_diff)),
                'direction': 'up' if time_diff > 0 else 'down' if time_diff < 0 else 'same'
            }
        }
    
    def export_data(self, start_date: date, end_date: date, format: str = 'json') -> str:
        """Export usage data for a date range."""
        data = {
            'export_date': datetime.now().isoformat(),
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'daily_data': []
        }
        
        current = start_date
        while current <= end_date:
            day_stats = self.get_day_stats(current)
            data['daily_data'].append({
                'date': current.isoformat(),
                'total_screen_time': day_stats.total_screen_time,
                'formatted_time': day_stats.formatted_time,
                'apps': [
                    {
                        'name': app['app_name'],
                        'duration': app['total_duration'],
                        'sessions': app['session_count']
                    }
                    for app in day_stats.app_breakdown
                ]
            })
            current += timedelta(days=1)
        
        if format == 'json':
            return json.dumps(data, indent=2)
        elif format == 'csv':
            return self._to_csv(data)
        else:
            return json.dumps(data, indent=2)
    
    # =========== Helper Methods ===========
    
    def _format_duration(self, seconds: int) -> str:
        """Format seconds into a human-readable string."""
        if seconds < 60:
            return f"{seconds}s"
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    def _get_day_name(self, date_str: str) -> str:
        """Get abbreviated day name from date string."""
        d = date.fromisoformat(date_str)
        return d.strftime('%a')
    
    def _get_top_apps_range(self, start_date: date, end_date: date, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top apps for a date range."""
        app_totals = {}
        
        current = start_date
        while current <= end_date:
            summary = self.db.get_app_usage_summary(current)
            for app in summary:
                name = app['app_name']
                if name not in app_totals:
                    app_totals[name] = {'app_name': name, 'total_duration': 0, 'session_count': 0}
                app_totals[name]['total_duration'] += app['total_duration']
                app_totals[name]['session_count'] += app['session_count']
            current += timedelta(days=1)
        
        # Sort by duration and take top N
        sorted_apps = sorted(
            app_totals.values(),
            key=lambda x: x['total_duration'],
            reverse=True
        )[:limit]
        
        # Add formatted duration
        for app in sorted_apps:
            app['formatted_duration'] = self._format_duration(app['total_duration'])
        
        return sorted_apps
    
    def _get_productivity_recommendation(self, score: float) -> str:
        """Get a productivity recommendation based on score."""
        if score >= 80:
            return "Excellent focus! Keep up the great work. 🎯"
        elif score >= 60:
            return "Good balance. Consider a few more focus sessions. 💪"
        elif score >= 40:
            return "Room for improvement. Try using Focus Mode more. 🎯"
        elif score >= 20:
            return "High distraction detected. Set app limits to help focus. ⚠️"
        else:
            return "Consider taking a digital detox break. 🌿"
    
    def _to_csv(self, data: Dict) -> str:
        """Convert data to CSV format."""
        lines = ["date,total_screen_time,app_name,app_duration,sessions"]
        
        for day in data['daily_data']:
            date_str = day['date']
            total = day['total_screen_time']
            
            if day['apps']:
                for app in day['apps']:
                    lines.append(
                        f"{date_str},{total},{app['name']},{app['duration']},{app['sessions']}"
                    )
            else:
                lines.append(f"{date_str},{total},,,")
        
        return '\n'.join(lines)


# Test
if __name__ == "__main__":
    stats = Stats()
    
    print("Today's Stats:")
    today = stats.get_today_stats()
    print(f"  Total time: {today.formatted_time}")
    print(f"  Unique apps: {today.unique_apps}")
    print(f"  Sessions: {today.session_count}")
    
    print("\nTop Apps:")
    for i, app in enumerate(today.app_breakdown[:5], 1):
        print(f"  {i}. {app['app_name']}: {app['formatted_duration']} ({app['percentage']}%)")
    
    print("\nWeekly Stats:")
    week = stats.get_week_stats()
    print(f"  Total: {stats._format_duration(week.total_screen_time)}")
    print(f"  Daily avg: {stats._format_duration(week.daily_average)}")
    print(f"  Trend: {week.trend}")
