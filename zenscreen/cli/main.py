"""
ZenScreen CLI - Command Line Interface for Digital Wellbeing.

A beautiful, colorful CLI for tracking screen time and managing focus.
"""

import click
from datetime import date, datetime, timedelta
from typing import Optional
import sys
import time

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich.style import Style
from rich.box import ROUNDED, HEAVY, DOUBLE
from rich import box

from zenscreen import __version__, __app_name__
from zenscreen.core.database import Database
from zenscreen.core.tracker import Tracker
from zenscreen.core.stats import Stats
from zenscreen.core.focus import FocusMode, FocusSession

# Initialize Rich console
console = Console()

# Color scheme
COLORS = {
    'primary': '#6366F1',      # Indigo
    'secondary': '#22C55E',    # Green
    'warning': '#F59E0B',      # Amber
    'danger': '#EF4444',       # Red
    'info': '#3B82F6',         # Blue
    'muted': '#6B7280',        # Gray
    'accent': '#8B5CF6',       # Purple
}


def format_duration(seconds: int) -> str:
    """Format seconds into a human-readable string."""
    if seconds < 60:
        return f"{seconds}s"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def get_time_color(seconds: int, goal_seconds: int = 28800) -> str:
    """Get color based on screen time vs goal."""
    ratio = seconds / goal_seconds
    
    if ratio < 0.5:
        return COLORS['secondary']  # Green - doing great
    elif ratio < 0.8:
        return COLORS['info']       # Blue - on track
    elif ratio < 1.0:
        return COLORS['warning']    # Amber - approaching limit
    else:
        return COLORS['danger']     # Red - exceeded


def create_progress_bar(value: float, max_value: float, width: int = 20, 
                        filled_char: str = '█', empty_char: str = '░') -> str:
    """Create a text-based progress bar."""
    if max_value <= 0:
        return empty_char * width
    
    ratio = min(1.0, value / max_value)
    filled = int(ratio * width)
    empty = width - filled
    
    return filled_char * filled + empty_char * empty


# =========== Main CLI Group ===========

@click.group()
@click.version_option(version=__version__, prog_name=__app_name__)
@click.pass_context
def cli(ctx):
    """
    🧘 ZenScreen - Digital Wellbeing for Linux
    
    Track your screen time, manage focus sessions, and build
    healthier digital habits.
    """
    ctx.ensure_object(dict)
    ctx.obj['db'] = Database()
    ctx.obj['stats'] = Stats(ctx.obj['db'])
    ctx.obj['focus'] = FocusMode(ctx.obj['db'])


# =========== Status Command ===========

@cli.command()
@click.pass_context
def status(ctx):
    """📊 Show current session and today's screen time."""
    stats = ctx.obj['stats']
    db = ctx.obj['db']
    focus = ctx.obj['focus']
    
    console.print()
    
    # Header
    console.print(Panel(
        f"[bold {COLORS['primary']}]🧘 ZenScreen[/] - [dim]Digital Wellbeing Dashboard[/]",
        box=ROUNDED
    ))
    
    # Get today's stats
    today_stats = stats.get_today_stats()
    goal_seconds = int(db.get_setting('daily_goal_minutes', '480')) * 60
    
    # Today's summary panel
    time_color = get_time_color(today_stats.total_screen_time, goal_seconds)
    progress_bar = create_progress_bar(today_stats.total_screen_time, goal_seconds, width=30)
    
    today_panel = f"""
[bold]Today's Screen Time[/]

[bold {time_color}]{today_stats.formatted_time}[/] / {format_duration(goal_seconds)}

[{time_color}]{progress_bar}[/] [{COLORS['muted']}]{today_stats.total_screen_time * 100 // goal_seconds}%[/]

[dim]Active apps: {today_stats.unique_apps} | Sessions: {today_stats.session_count}[/]
"""
    
    console.print(Panel(today_panel.strip(), title="📈 Today", border_style=time_color))
    
    # Top apps table
    if today_stats.app_breakdown:
        table = Table(
            title="🏆 Top Applications",
            box=ROUNDED,
            header_style=f"bold {COLORS['primary']}",
            title_style=f"bold {COLORS['accent']}"
        )
        
        table.add_column("App", style="bold")
        table.add_column("Time", justify="right")
        table.add_column("Usage", justify="left", width=25)
        table.add_column("%", justify="right")
        
        for i, app in enumerate(today_stats.app_breakdown[:5]):
            pct = app['percentage']
            bar = create_progress_bar(pct, 100, width=15)
            
            # Color based on percentage
            if pct > 50:
                bar_color = COLORS['danger']
            elif pct > 30:
                bar_color = COLORS['warning']
            else:
                bar_color = COLORS['secondary']
            
            rank = ['🥇', '🥈', '🥉', '4.', '5.'][i] if i < 5 else f'{i+1}.'
            
            table.add_row(
                f"{rank} {app['app_name']}",
                app['formatted_duration'],
                f"[{bar_color}]{bar}[/]",
                f"{pct:.1f}%"
            )
        
        console.print(table)
    else:
        console.print(Panel(
            "[dim]No activity recorded today. Start using your computer![/]",
            border_style=COLORS['muted']
        ))
    
    # Active focus session
    focus_info = focus.get_session_info()
    if focus_info:
        focus_panel = f"""
[bold {COLORS['accent']}]🎯 Focus Session Active[/]

Time remaining: [bold]{focus_info['formatted_remaining']}[/]
Progress: [{COLORS['accent']}]{create_progress_bar(focus_info['progress_percent'], 100, width=30)}[/] {focus_info['progress_percent']:.1f}%

Blocked apps: [dim]{', '.join(focus_info['blocked_apps']) or 'None'}[/]
"""
        console.print(Panel(focus_panel.strip(), border_style=COLORS['accent']))
    
    # Productivity score
    productivity = stats.get_productivity_score()
    score = productivity['score']
    
    if score >= 70:
        score_color = COLORS['secondary']
        score_icon = '🌟'
    elif score >= 40:
        score_color = COLORS['warning']
        score_icon = '📊'
    else:
        score_color = COLORS['danger']
        score_icon = '⚠️'
    
    console.print(Panel(
        f"{score_icon} [bold]Productivity Score:[/] [{score_color}]{score:.0f}/100[/]\n\n[dim]{productivity['recommendation']}[/]",
        title="💡 Insight",
        border_style=score_color
    ))
    
    console.print()


# =========== Report Command ===========

@cli.command()
@click.option('--today', 'period', flag_value='today', default=True, help='Show today\'s report')
@click.option('--week', 'period', flag_value='week', help='Show weekly report')
@click.option('--month', 'period', flag_value='month', help='Show monthly report')
@click.option('--date', 'specific_date', type=str, help='Show report for specific date (YYYY-MM-DD)')
@click.pass_context
def report(ctx, period: str, specific_date: Optional[str]):
    """📈 View detailed usage reports."""
    stats = ctx.obj['stats']
    
    console.print()
    
    if specific_date:
        try:
            target_date = date.fromisoformat(specific_date)
            show_daily_report(stats, target_date)
        except ValueError:
            console.print(f"[{COLORS['danger']}]Invalid date format. Use YYYY-MM-DD[/]")
            return
    elif period == 'week':
        show_weekly_report(stats)
    elif period == 'month':
        show_monthly_report(stats)
    else:
        show_daily_report(stats, date.today())
    
    console.print()


def show_daily_report(stats: Stats, target_date: date):
    """Display detailed daily report."""
    day_stats = stats.get_day_stats(target_date)
    
    date_str = target_date.strftime('%A, %B %d, %Y')
    
    console.print(Panel(
        f"[bold {COLORS['primary']}]📅 Daily Report[/] - {date_str}",
        box=ROUNDED
    ))
    
    # Summary
    summary = f"""
[bold]Total Screen Time:[/] [{COLORS['primary']}]{day_stats.formatted_time}[/]
[bold]Active Applications:[/] {day_stats.unique_apps}
[bold]Total Sessions:[/] {day_stats.session_count}
"""
    
    if day_stats.first_activity:
        try:
            first = datetime.fromisoformat(day_stats.first_activity).strftime('%H:%M')
            summary += f"[bold]First Activity:[/] {first}\n"
        except:
            pass
    
    if day_stats.last_activity:
        try:
            last = datetime.fromisoformat(day_stats.last_activity).strftime('%H:%M')
            summary += f"[bold]Last Activity:[/] {last}\n"
        except:
            pass
    
    console.print(Panel(summary.strip(), title="📊 Summary", border_style=COLORS['info']))
    
    # App breakdown
    if day_stats.app_breakdown:
        table = Table(
            title="📱 Application Breakdown",
            box=ROUNDED,
            header_style=f"bold {COLORS['primary']}"
        )
        
        table.add_column("#", style="dim", width=4)
        table.add_column("Application", style="bold")
        table.add_column("Duration", justify="right")
        table.add_column("Sessions", justify="center")
        table.add_column("Share", justify="left", width=20)
        
        for i, app in enumerate(day_stats.app_breakdown, 1):
            pct = app['percentage']
            bar = create_progress_bar(pct, 100, width=15)
            
            table.add_row(
                str(i),
                app['app_name'],
                app['formatted_duration'],
                str(app['session_count']),
                f"[{COLORS['accent']}]{bar}[/] {pct:.1f}%"
            )
        
        console.print(table)
    
    # Productivity
    productivity = stats.get_productivity_score(target_date)
    console.print(Panel(
        f"[bold]Score:[/] [{COLORS['secondary'] if productivity['score'] >= 50 else COLORS['danger']}]{productivity['score']:.0f}%[/]\n"
        f"[bold]Productive:[/] {productivity['productive_formatted']} | "
        f"[bold]Neutral:[/] {format_duration(productivity['neutral_time'])} | "
        f"[bold]Distracting:[/] {productivity['unproductive_formatted']}",
        title="💼 Productivity",
        border_style=COLORS['accent']
    ))


def show_weekly_report(stats: Stats):
    """Display weekly report with visualization."""
    week_stats = stats.get_week_stats()
    
    console.print(Panel(
        f"[bold {COLORS['primary']}]📅 Weekly Report[/] - Last 7 Days",
        box=ROUNDED
    ))
    
    # Summary
    trend_icon = {'up': '📈', 'down': '📉', 'stable': '➡️'}[week_stats.trend]
    trend_color = {
        'up': COLORS['danger'],
        'down': COLORS['secondary'],
        'stable': COLORS['info']
    }[week_stats.trend]
    
    summary = f"""
[bold]Total Screen Time:[/] [{COLORS['primary']}]{format_duration(week_stats.total_screen_time)}[/]
[bold]Daily Average:[/] {format_duration(week_stats.daily_average)}
[bold]Trend:[/] [{trend_color}]{trend_icon} {week_stats.trend.title()}[/]
[bold]Busiest Day:[/] {week_stats.busiest_day or 'N/A'}
"""
    console.print(Panel(summary.strip(), title="📊 Summary", border_style=COLORS['info']))
    
    # Weekly chart (ASCII bar chart)
    max_duration = max((d['total_duration'] for d in week_stats.days), default=1)
    
    chart_lines = ["", "[bold]Daily Usage Chart[/]", ""]
    
    for day in week_stats.days:
        bar_length = int((day['total_duration'] / max_duration) * 30) if max_duration > 0 else 0
        bar = '█' * bar_length + '░' * (30 - bar_length)
        
        day_name = day['day_name']
        duration = day['formatted_duration'] or '0m'
        
        # Highlight today
        is_today = day['date'] == date.today().isoformat()
        style = f"bold {COLORS['accent']}" if is_today else COLORS['info']
        
        chart_lines.append(f"  [{style}]{day_name:3}[/] [{COLORS['primary']}]{bar}[/] {duration:>7}")
    
    chart_lines.append("")
    
    console.print(Panel('\n'.join(chart_lines), border_style=COLORS['accent']))
    
    # Top apps for the week
    if week_stats.most_used_apps:
        table = Table(title="🏆 Most Used Apps (This Week)", box=ROUNDED)
        table.add_column("App", style="bold")
        table.add_column("Total Time", justify="right")
        table.add_column("Sessions", justify="center")
        
        for app in week_stats.most_used_apps:
            table.add_row(
                app['app_name'],
                app['formatted_duration'],
                str(app['session_count'])
            )
        
        console.print(table)


def show_monthly_report(stats: Stats):
    """Display monthly report."""
    today = date.today()
    month_stats = stats.get_month_stats(today.year, today.month)
    
    month_name = today.strftime('%B %Y')
    
    console.print(Panel(
        f"[bold {COLORS['primary']}]📅 Monthly Report[/] - {month_name}",
        box=ROUNDED
    ))
    
    # Summary
    summary = f"""
[bold]Total Screen Time:[/] [{COLORS['primary']}]{format_duration(month_stats['total_screen_time'])}[/]
[bold]Days Tracked:[/] {month_stats['days_tracked']}
[bold]Daily Average:[/] {format_duration(month_stats['average_daily'])}
"""
    console.print(Panel(summary.strip(), title="📊 Summary", border_style=COLORS['info']))
    
    # Top apps
    if month_stats['top_apps']:
        table = Table(title="🏆 Top Applications (This Month)", box=ROUNDED)
        table.add_column("#", width=4, style="dim")
        table.add_column("Application", style="bold")
        table.add_column("Total Time", justify="right")
        
        for i, app in enumerate(month_stats['top_apps'], 1):
            table.add_row(
                str(i),
                app['app_name'],
                format_duration(app['total_duration'])
            )
        
        console.print(table)


# =========== Focus Command ===========

@cli.group()
@click.pass_context
def focus(ctx):
    """🎯 Manage focus sessions for distraction-free work."""
    pass


@focus.command('start')
@click.option('--duration', '-d', type=int, default=25, help='Duration in minutes (default: 25)')
@click.option('--block', '-b', multiple=True, help='Apps to block during session')
@click.option('--preset', '-p', type=click.Choice(['pomodoro', 'short', 'medium', 'long', 'deep_work']),
              help='Use a duration preset')
@click.option('--block-preset', type=click.Choice(['social', 'video', 'browsing', 'games', 'all']),
              help='Use a blocking preset')
@click.pass_context
def focus_start(ctx, duration: int, block: tuple, preset: Optional[str], block_preset: Optional[str]):
    """Start a new focus session."""
    focus_mode = ctx.obj['focus']
    
    if focus_mode.is_active:
        console.print(f"[{COLORS['warning']}]⚠️  A focus session is already active![/]")
        return
    
    blocked_apps = list(block) if block else None
    
    try:
        session = focus_mode.start_session(
            duration_minutes=duration,
            blocked_apps=blocked_apps,
            use_preset=preset,
            block_preset=block_preset
        )
        
        console.print()
        console.print(Panel(
            f"[bold {COLORS['accent']}]🎯 Focus Session Started![/]\n\n"
            f"[bold]Duration:[/] {session.planned_duration // 60} minutes\n"
            f"[bold]Blocked apps:[/] {', '.join(session.blocked_apps) or 'None'}\n\n"
            f"[dim]Stay focused! You've got this! 💪[/]",
            border_style=COLORS['accent']
        ))
        
        # Show live progress
        console.print("\n[dim]Press Ctrl+C to stop the session[/]\n")
        
        try:
            with Live(console=console, refresh_per_second=1) as live:
                while focus_mode.is_active:
                    info = focus_mode.get_session_info()
                    if not info:
                        break
                    
                    progress_bar = create_progress_bar(
                        info['progress_percent'], 100, width=40
                    )
                    
                    panel = Panel(
                        f"\n[bold {COLORS['accent']}]⏱️  {info['formatted_remaining']}[/] remaining\n\n"
                        f"[{COLORS['primary']}]{progress_bar}[/] {info['progress_percent']:.1f}%\n",
                        title="🎯 Focus Mode",
                        border_style=COLORS['accent']
                    )
                    
                    live.update(panel)
                    time.sleep(1)
        except KeyboardInterrupt:
            focus_mode.stop_session(completed=False)
            console.print(f"\n[{COLORS['warning']}]Session interrupted.[/]")
            return
        
        console.print(f"\n[{COLORS['secondary']}]✨ Focus session completed! Great work![/]")
        
    except Exception as e:
        console.print(f"[{COLORS['danger']}]Error: {e}[/]")


@focus.command('stop')
@click.pass_context
def focus_stop(ctx):
    """Stop the current focus session."""
    focus_mode = ctx.obj['focus']
    
    if not focus_mode.is_active:
        console.print(f"[{COLORS['muted']}]No active focus session.[/]")
        return
    
    session = focus_mode.stop_session(completed=False)
    
    if session:
        elapsed_mins = session.elapsed_seconds // 60
        console.print(f"[{COLORS['warning']}]Focus session stopped after {elapsed_mins} minutes.[/]")


@focus.command('status')
@click.pass_context
def focus_status(ctx):
    """Show current focus session status."""
    focus_mode = ctx.obj['focus']
    
    info = focus_mode.get_session_info()
    
    if not info:
        console.print(f"[{COLORS['muted']}]No active focus session.[/]")
        console.print(f"\n[dim]Start a session with:[/] zenscreen focus start")
        return
    
    progress_bar = create_progress_bar(info['progress_percent'], 100, width=40)
    
    console.print(Panel(
        f"[bold {COLORS['accent']}]🎯 Focus Session Active[/]\n\n"
        f"[bold]Time remaining:[/] {info['formatted_remaining']}\n"
        f"[bold]Progress:[/] [{COLORS['primary']}]{progress_bar}[/] {info['progress_percent']:.1f}%\n"
        f"[bold]Blocked apps:[/] {', '.join(info['blocked_apps']) or 'None'}",
        border_style=COLORS['accent']
    ))


@focus.command('history')
@click.option('--days', '-d', type=int, default=7, help='Number of days to show')
@click.pass_context
def focus_history(ctx, days: int):
    """Show focus session history."""
    stats = ctx.obj['stats']
    db = ctx.obj['db']
    
    focus_stats = stats.get_focus_stats(days)
    history = db.get_focus_history(days)
    
    console.print()
    console.print(Panel(
        f"[bold {COLORS['primary']}]🎯 Focus History[/] - Last {days} days",
        box=ROUNDED
    ))
    
    # Stats summary
    if focus_stats.total_sessions > 0:
        summary = f"""
[bold]Total Sessions:[/] {focus_stats.total_sessions}
[bold]Completed:[/] {focus_stats.completed_sessions} ({focus_stats.completion_rate:.1f}%)
[bold]Total Focus Time:[/] {format_duration(focus_stats.total_focus_time)}
[bold]Average Session:[/] {format_duration(focus_stats.average_session_length)}
"""
        console.print(Panel(summary.strip(), title="📊 Summary", border_style=COLORS['info']))
        
        # Recent sessions table
        if history:
            table = Table(title="📋 Recent Sessions", box=ROUNDED)
            table.add_column("Date", style="dim")
            table.add_column("Duration", justify="right")
            table.add_column("Status")
            table.add_column("Blocked Apps")
            
            for session in history[:10]:
                start = datetime.fromisoformat(session['start_time'])
                date_str = start.strftime('%m/%d %H:%M')
                duration = format_duration(session.get('actual_duration', 0))
                
                if session.get('completed'):
                    status = f"[{COLORS['secondary']}]✓ Complete[/]"
                elif session.get('interrupted'):
                    status = f"[{COLORS['warning']}]✗ Interrupted[/]"
                else:
                    status = f"[{COLORS['muted']}]? Unknown[/]"
                
                apps = ', '.join(session.get('blocked_apps', [])[:3]) or '-'
                if len(session.get('blocked_apps', [])) > 3:
                    apps += f" (+{len(session['blocked_apps']) - 3})"
                
                table.add_row(date_str, duration, status, apps)
            
            console.print(table)
    else:
        console.print(f"[{COLORS['muted']}]No focus sessions recorded yet.[/]")
        console.print(f"\n[dim]Start your first session with:[/] zenscreen focus start")
    
    console.print()


# =========== Config Command ===========

@cli.group()
@click.pass_context
def config(ctx):
    """⚙️  Manage ZenScreen configuration."""
    pass


@config.command('list')
@click.pass_context
def config_list(ctx):
    """List all configuration options."""
    db = ctx.obj['db']
    settings = db.get_all_settings()
    
    console.print()
    console.print(Panel(
        f"[bold {COLORS['primary']}]⚙️  ZenScreen Configuration[/]",
        box=ROUNDED
    ))
    
    table = Table(box=ROUNDED)
    table.add_column("Setting", style="bold")
    table.add_column("Value")
    table.add_column("Description", style="dim")
    
    descriptions = {
        'idle_threshold': 'Seconds before marking user as idle',
        'break_reminder_interval': 'Seconds between break reminders',
        'daily_goal_minutes': 'Daily screen time goal in minutes',
        'enable_notifications': 'Enable desktop notifications',
        'theme': 'Color theme (system/light/dark)',
        'start_on_login': 'Start tracking on login',
        'track_window_titles': 'Track window titles (privacy)',
        'focus_default_duration': 'Default focus session duration (seconds)',
    }
    
    for key, value in settings.items():
        desc = descriptions.get(key, '')
        table.add_row(key, value, desc)
    
    console.print(table)
    console.print()


@config.command('set')
@click.argument('key')
@click.argument('value')
@click.pass_context
def config_set(ctx, key: str, value: str):
    """Set a configuration option."""
    db = ctx.obj['db']
    
    valid_keys = [
        'idle_threshold', 'break_reminder_interval', 'daily_goal_minutes',
        'enable_notifications', 'theme', 'start_on_login', 
        'track_window_titles', 'focus_default_duration'
    ]
    
    if key not in valid_keys:
        console.print(f"[{COLORS['danger']}]Unknown setting: {key}[/]")
        console.print(f"[dim]Valid settings: {', '.join(valid_keys)}[/]")
        return
    
    db.set_setting(key, value)
    console.print(f"[{COLORS['secondary']}]✓ Set {key} = {value}[/]")


@config.command('get')
@click.argument('key')
@click.pass_context
def config_get(ctx, key: str):
    """Get a configuration option."""
    db = ctx.obj['db']
    value = db.get_setting(key)
    
    if value is not None:
        console.print(f"[bold]{key}[/] = [{COLORS['primary']}]{value}[/]")
    else:
        console.print(f"[{COLORS['muted']}]Setting '{key}' not found[/]")


# =========== Daemon Command ===========

@cli.group()
@click.pass_context
def daemon(ctx):
    """🔄 Control the background tracking service."""
    pass


@daemon.command('start')
@click.option('--foreground', '-f', is_flag=True, help='Run in foreground (for debugging)')
@click.pass_context
def daemon_start(ctx, foreground: bool):
    """Start the tracking daemon."""
    if foreground:
        console.print(f"[{COLORS['info']}]Starting tracker in foreground mode...[/]")
        console.print("[dim]Press Ctrl+C to stop[/]\n")
        
        db = ctx.obj['db']
        tracker = Tracker(poll_interval=1.0, idle_threshold=300)
        
        def on_window_change(window):
            console.print(f"[{COLORS['muted']}]{datetime.now().strftime('%H:%M:%S')}[/] → [{COLORS['primary']}]{window.app_name}[/]")
        
        tracker.set_on_window_change(on_window_change)
        tracker.start(database=db)
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            console.print(f"\n[{COLORS['warning']}]Stopping tracker...[/]")
            tracker.stop()
    else:
        # For background mode, we'd typically use systemd
        console.print(f"[{COLORS['info']}]To run the daemon as a background service, use:[/]")
        console.print("  systemctl --user start zenscreen")
        console.print(f"\n[dim]Or run in foreground mode with:[/] zenscreen daemon start --foreground")


@daemon.command('stop')
@click.pass_context
def daemon_stop(ctx):
    """Stop the tracking daemon."""
    console.print(f"[{COLORS['info']}]To stop the daemon service, use:[/]")
    console.print("  systemctl --user stop zenscreen")


@daemon.command('status')
@click.pass_context
def daemon_status(ctx):
    """Show daemon status."""
    import subprocess
    
    try:
        result = subprocess.run(
            ['systemctl', '--user', 'is-active', 'zenscreen'],
            capture_output=True, text=True
        )
        
        if result.stdout.strip() == 'active':
            console.print(f"[{COLORS['secondary']}]● zenscreen daemon is running[/]")
        else:
            console.print(f"[{COLORS['muted']}]○ zenscreen daemon is not running[/]")
    except Exception:
        console.print(f"[{COLORS['muted']}]Could not check daemon status[/]")
        console.print("[dim]The daemon can be started with: zenscreen daemon start --foreground[/]")


# =========== Export Command ===========

@cli.command()
@click.option('--format', '-f', type=click.Choice(['json', 'csv']), default='json',
              help='Export format')
@click.option('--days', '-d', type=int, default=30, help='Number of days to export')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.pass_context
def export(ctx, format: str, days: int, output: Optional[str]):
    """📤 Export usage data to JSON or CSV."""
    stats = ctx.obj['stats']
    
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)
    
    data = stats.export_data(start_date, end_date, format=format)
    
    if output:
        with open(output, 'w') as f:
            f.write(data)
        console.print(f"[{COLORS['secondary']}]✓ Exported {days} days of data to {output}[/]")
    else:
        console.print(data)


# =========== Entry Point ===========

def main():
    """Main entry point."""
    cli(obj={})


if __name__ == "__main__":
    main()
