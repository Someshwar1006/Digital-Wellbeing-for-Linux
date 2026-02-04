"""
ZenScreen GTK4 Application - Main Window and Application Setup.

A modern, beautiful desktop application for digital wellbeing.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio, GLib, Gdk
import sys
import threading
import math
import cairo
from datetime import date, datetime
from typing import List, Dict, Any

from zenscreen import __version__, __app_name__, __app_id__
from zenscreen.core.database import Database
from zenscreen.core.tracker import Tracker
from zenscreen.core.stats import Stats
from zenscreen.core.focus import FocusMode


# CSS Styling for the application
CSS = """
/* Base Theme */
window {
    background-color: @window_bg_color;
}

/* Header Styling */
.title-large {
    font-size: 32px;
    font-weight: 800;
}

.title-medium {
    font-size: 24px;
    font-weight: 700;
}

.title-small {
    font-size: 18px;
    font-weight: 600;
}

/* Cards */
.card {
    background-color: @card_bg_color;
    border-radius: 16px;
    padding: 24px;
    margin: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.stat-card {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
    border-radius: 20px;
    padding: 24px;
    color: white;
}

.stat-card-green {
    background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
}

.stat-card-amber {
    background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
}

.stat-card-red {
    background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
}

/* Progress Ring Placeholder */
.progress-ring {
    min-width: 120px;
    min-height: 120px;
}

/* App Usage Bar */
.usage-bar {
    background-color: alpha(@accent_color, 0.2);
    border-radius: 8px;
    min-height: 12px;
}

.usage-bar-fill {
    background-color: @accent_color;
    border-radius: 8px;
}

/* Focus Mode Card */
.focus-card {
    background: linear-gradient(135deg, #8b5cf6 0%, #a855f7 100%);
    border-radius: 20px;
    padding: 32px;
    color: white;
}

.focus-timer {
    font-size: 64px;
    font-weight: 800;
    font-family: monospace;
}

/* Action Buttons */
.suggested-action {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
    color: white;
    border-radius: 12px;
    padding: 12px 24px;
    font-weight: 600;
}

.destructive-action {
    background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
}

/* Sidebar */
.sidebar {
    background-color: @sidebar_bg_color;
}

/* Week Chart */
.week-bar {
    background-color: alpha(@accent_color, 0.3);
    border-radius: 4px;
}

.week-bar-fill {
    background-color: @accent_color;
    border-radius: 4px;
    transition: all 300ms ease;
}

/* Badge */
.badge {
    background-color: @accent_color;
    border-radius: 12px;
    padding: 4px 12px;
    font-size: 12px;
    font-weight: 600;
}

.badge-success {
    background-color: #22c55e;
    color: white;
}

.badge-warning {
    background-color: #f59e0b;
    color: white;
}

.badge-danger {
    background-color: #ef4444;
    color: white;
}

/* Dim text */
.dim-label {
    opacity: 0.7;
}

/* Large Value Display */
.value-large {
    font-size: 48px;
    font-weight: 800;
}

.value-medium {
    font-size: 32px;
    font-weight: 700;
}

/* Empty State */
.empty-state {
    opacity: 0.5;
}

/* Animation classes */
@keyframes pulse {
    0% { opacity: 1; }
    50% { opacity: 0.5; }
    100% { opacity: 1; }
}

.pulse {
    animation: pulse 2s ease-in-out infinite;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes slideIn {
    from { opacity: 0; transform: translateX(-20px); }
    to { opacity: 1; transform: translateX(0); }
}

@keyframes scaleIn {
    from { opacity: 0; transform: scale(0.9); }
    to { opacity: 1; transform: scale(1); }
}

@keyframes glow {
    0% { box-shadow: 0 0 5px alpha(@accent_color, 0.3); }
    50% { box-shadow: 0 0 20px alpha(@accent_color, 0.6); }
    100% { box-shadow: 0 0 5px alpha(@accent_color, 0.3); }
}

.fade-in {
    animation: fadeIn 0.4s ease-out;
}

.slide-in {
    animation: slideIn 0.3s ease-out;
}

.scale-in {
    animation: scaleIn 0.3s ease-out;
}

/* Smooth transitions for interactive elements */
.card {
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
}

.suggested-action, .destructive-action {
    transition: transform 0.15s ease, filter 0.15s ease;
}

.suggested-action:hover, .destructive-action:hover {
    transform: scale(1.02);
    filter: brightness(1.1);
}

.suggested-action:active, .destructive-action:active {
    transform: scale(0.98);
}

.app-legend-item {
    transition: background-color 0.2s ease, transform 0.15s ease;
}

.app-legend-item:hover {
    transform: translateX(4px);
}

/* Progress bar animations */
progressbar progress {
    transition: all 0.5s ease-out;
}

/* Focus glow effect */
.focus-active {
    animation: glow 2s ease-in-out infinite;
}

/* Donut Chart */
.donut-card {
    background-color: #1a1a2e;
    border-radius: 24px;
    padding: 32px;
}

.donut-chart {
    min-width: 280px;
    min-height: 280px;
}

.app-legend-item {
    padding: 8px 12px;
    border-radius: 8px;
    margin: 4px 0;
}

.app-legend-item:hover {
    background-color: alpha(@accent_color, 0.1);
}

/* Settings */
.settings-row {
    padding: 16px;
    border-radius: 12px;
    margin: 4px 0;
}
"""

# Colors for the donut chart segments
CHART_COLORS = [
    (0.388, 0.400, 0.945),   # Indigo #6366f1
    (0.545, 0.361, 0.965),   # Purple #8b5cf6
    (0.133, 0.773, 0.369),   # Green #22c55e
    (0.961, 0.620, 0.043),   # Amber #f59e0b
    (0.937, 0.267, 0.267),   # Red #ef4444
    (0.231, 0.706, 0.882),   # Cyan #3bb4e1
    (0.976, 0.451, 0.455),   # Pink #f97373
    (0.404, 0.827, 0.537),   # Light green #67d389
    (0.733, 0.533, 0.933),   # Violet #bb88ee
    (0.988, 0.761, 0.400),   # Yellow #fcc266
]


class DonutChartWidget(Gtk.DrawingArea):
    """A custom widget that draws a donut chart for app usage with hover effects."""
    
    def __init__(self):
        super().__init__()
        
        self.data: List[Dict[str, Any]] = []
        self.total_time_str = "0h 0m"
        self.hover_index = -1  # Which segment is being hovered
        self.hover_info = None  # Tooltip text
        
        self.set_size_request(280, 280)
        self.set_draw_func(self._draw)
        
        # Add motion controller for hover detection
        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self._on_motion)
        motion.connect("leave", self._on_leave)
        self.add_controller(motion)
        
        # Store segment angles for hit detection
        self.segment_angles = []
    
    def set_data(self, apps: List[Dict[str, Any]], total_time: str):
        """Update the chart data."""
        self.data = apps[:8]  # Max 8 segments for clarity
        self.total_time_str = total_time
        self._calculate_segments()
        self.queue_draw()
    
    def _calculate_segments(self):
        """Pre-calculate segment angles for hit detection."""
        self.segment_angles = []
        if not self.data:
            return
        
        total = sum(app.get('duration', 0) for app in self.data)
        if total == 0:
            return
        
        start_angle = -math.pi / 2
        for app in self.data:
            duration = app.get('duration', 0)
            fraction = duration / total
            sweep_angle = fraction * 2 * math.pi
            self.segment_angles.append((start_angle, start_angle + sweep_angle))
            start_angle += sweep_angle
    
    def _on_motion(self, controller, x, y):
        """Handle mouse motion for hover detection."""
        width = self.get_width()
        height = self.get_height()
        center_x = width / 2
        center_y = height / 2
        
        # Calculate distance and angle from center
        dx = x - center_x
        dy = y - center_y
        distance = math.sqrt(dx * dx + dy * dy)
        angle = math.atan2(dy, dx)
        
        outer_radius = min(width, height) / 2 - 10
        inner_radius = outer_radius * 0.6
        
        old_hover = self.hover_index
        self.hover_index = -1
        self.hover_info = None
        
        # Check if within donut ring
        if inner_radius < distance < outer_radius:
            # Find which segment
            for i, (start, end) in enumerate(self.segment_angles):
                # Normalize angle to match segment angles
                norm_angle = angle
                if norm_angle < -math.pi / 2:
                    norm_angle += 2 * math.pi
                
                # Check if angle is within segment
                if start <= norm_angle < end or (start <= norm_angle + 2 * math.pi < end):
                    self.hover_index = i
                    if i < len(self.data):
                        app = self.data[i]
                        self.hover_info = f"{app.get('app_name', 'Unknown')}: {app.get('formatted_duration', '0m')}"
                    break
        
        if old_hover != self.hover_index:
            self.queue_draw()
    
    def _on_leave(self, controller):
        """Handle mouse leaving the widget."""
        self.hover_index = -1
        self.hover_info = None
        self.queue_draw()
    
    def _draw(self, area, cr, width, height):
        """Draw the donut chart using Cairo."""
        # Calculate dimensions
        center_x = width / 2
        center_y = height / 2
        outer_radius = min(width, height) / 2 - 10
        inner_radius = outer_radius * 0.6  # Donut hole size
        
        # Background (dark)
        cr.set_source_rgb(0.1, 0.1, 0.18)
        cr.arc(center_x, center_y, outer_radius + 5, 0, 2 * math.pi)
        cr.fill()
        
        if not self.data:
            # Empty state - draw full gray ring
            cr.set_source_rgb(0.2, 0.2, 0.3)
            cr.set_line_width(outer_radius - inner_radius)
            cr.arc(center_x, center_y, (outer_radius + inner_radius) / 2, 0, 2 * math.pi)
            cr.stroke()
        else:
            # Calculate total for percentages
            total = sum(app.get('duration', 0) for app in self.data)
            if total == 0:
                total = 1
            
            # Draw segments
            start_angle = -math.pi / 2  # Start from top
            
            for i, app in enumerate(self.data):
                duration = app.get('duration', 0)
                fraction = duration / total
                sweep_angle = fraction * 2 * math.pi
                
                if sweep_angle < 0.02:  # Skip tiny segments
                    start_angle += sweep_angle
                    continue
                
                # Get color - use from data if available (for categories)
                if 'color' in app:
                    color = app['color']
                else:
                    color = CHART_COLORS[i % len(CHART_COLORS)]
                
                # Highlight if hovered
                if i == self.hover_index:
                    # Brighter color for hover
                    cr.set_source_rgb(
                        min(1.0, color[0] * 1.3),
                        min(1.0, color[1] * 1.3),
                        min(1.0, color[2] * 1.3)
                    )
                    # Slightly larger
                    cr.set_line_width(outer_radius - inner_radius + 8)
                else:
                    cr.set_source_rgb(*color)
                    cr.set_line_width(outer_radius - inner_radius)
                
                # Draw arc segment
                cr.arc(center_x, center_y, (outer_radius + inner_radius) / 2,
                       start_angle, start_angle + sweep_angle - 0.02)  # Small gap between segments
                cr.stroke()
                
                start_angle += sweep_angle
        
        # Draw center circle (donut hole)
        cr.set_source_rgb(0.1, 0.1, 0.18)
        cr.arc(center_x, center_y, inner_radius - 2, 0, 2 * math.pi)
        cr.fill()
        
        # Draw center text
        if self.hover_info:
            # Show hovered app info in center
            cr.set_source_rgb(1, 1, 1)
            cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(14)
            extents = cr.text_extents(self.hover_info)
            # Truncate if too long
            display_text = self.hover_info if extents.width < inner_radius * 1.6 else self.hover_info[:15] + "..."
            extents = cr.text_extents(display_text)
            cr.move_to(center_x - extents.width / 2, center_y + 5)
            cr.show_text(display_text)
        else:
            # Show "TODAY" label
            cr.set_source_rgb(0.6, 0.6, 0.7)
            cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            cr.set_font_size(12)
            today_text = "TODAY"
            extents = cr.text_extents(today_text)
            cr.move_to(center_x - extents.width / 2, center_y - 15)
            cr.show_text(today_text)
            
            # Show time
            cr.set_source_rgb(1, 1, 1)
            cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(24)
            extents = cr.text_extents(self.total_time_str)
            cr.move_to(center_x - extents.width / 2, center_y + 12)
            cr.show_text(self.total_time_str)


class ZenScreenApp(Adw.Application):
    """Main ZenScreen GTK4 Application."""
    
    def __init__(self):
        super().__init__(
            application_id=__app_id__,
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        
        # Initialize core components
        self.db = Database()
        self.stats = Stats(self.db)
        self.focus = FocusMode(self.db)
        self.tracker = Tracker()
        
        # UI state
        self._update_timer_id = None
        self._focus_timer_id = None
        
    def do_startup(self):
        """Called when the application starts."""
        Adw.Application.do_startup(self)
        
        # Load CSS
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(CSS.encode())
        
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        
        # Create actions
        self._create_actions()
    
    def do_activate(self):
        """Called when the application is activated."""
        win = self.props.active_window
        if not win:
            win = ZenScreenWindow(application=self)
        win.present()
        
        # Start update timer
        self._start_update_timer()
    
    def do_shutdown(self):
        """Called when the application shuts down."""
        if self._update_timer_id:
            GLib.source_remove(self._update_timer_id)
        if self._focus_timer_id:
            GLib.source_remove(self._focus_timer_id)
        
        Adw.Application.do_shutdown(self)
    
    def _create_actions(self):
        """Create application actions."""
        # About action
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        self.add_action(about_action)
        
        # Quit action
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", self._on_quit)
        self.add_action(quit_action)
        self.set_accels_for_action("app.quit", ["<Control>q"])
    
    def _on_about(self, action, param):
        """Show about dialog."""
        about = Adw.AboutWindow(
            transient_for=self.props.active_window,
            application_name=__app_name__,
            application_icon=__app_id__,
            developer_name="ZenScreen Team",
            version=__version__,
            copyright="© 2024 ZenScreen",
            license_type=Gtk.License.GPL_3_0,
            website="https://github.com/zenscreen/zenscreen",
            issue_url="https://github.com/zenscreen/zenscreen/issues",
            developers=["someshwar"],
            designers=["someshwar"],
        )
        about.add_credit_section("Special Thanks", ["The GNOME Team", "GTK4 Contributors"])
        about.present()
    
    def _on_quit(self, action, param):
        """Quit the application."""
        self.quit()
    
    def _start_update_timer(self):
        """Start the periodic UI update timer."""
        def update():
            win = self.props.active_window
            if win and hasattr(win, 'update_stats'):
                win.update_stats()
            return True
        
        # Update every 30 seconds
        self._update_timer_id = GLib.timeout_add_seconds(30, update)


class ZenScreenWindow(Adw.ApplicationWindow):
    """Main application window."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.app = kwargs.get('application')
        
        self.set_title(__app_name__)
        self.set_default_size(1000, 700)
        
        # Set window icon for taskbar (uses the app's own icon)
        self.set_icon_name("com.zenscreen.app")
        
        # Main layout
        self._build_ui()
        
        # Initial data load
        GLib.idle_add(self.update_stats)
        
        # Update goal label with current setting
        GLib.idle_add(self._update_goal_display)
    
    def _build_ui(self):
        """Build the main UI."""
        # Main box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        # Header bar
        header = Adw.HeaderBar()
        header.set_title_widget(self._create_title_widget())
        
        # Menu button
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu_button.set_menu_model(self._create_menu())
        header.pack_end(menu_button)
        
        # Refresh button
        refresh_button = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_button.connect("clicked", lambda _: self.update_stats())
        refresh_button.set_tooltip_text("Refresh")
        header.pack_end(refresh_button)
        
        # Settings button
        settings_button = Gtk.Button(icon_name="emblem-system-symbolic")
        settings_button.connect("clicked", self._on_settings_clicked)
        settings_button.set_tooltip_text("Settings")
        header.pack_start(settings_button)
        
        main_box.append(header)
        
        # Navigation view with pages
        self.nav_view = Adw.NavigationView()
        self.nav_view.set_vexpand(True)
        
        # Dashboard page
        dashboard_page = Adw.NavigationPage(title="Dashboard")
        dashboard_page.set_child(self._create_dashboard())
        self.nav_view.push(dashboard_page)
        
        main_box.append(self.nav_view)
        
        self.set_content(main_box)
    
    def _create_title_widget(self):
        """Create the header title widget."""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_halign(Gtk.Align.CENTER)
        
        # Icon
        icon = Gtk.Image.new_from_icon_name("preferences-desktop-apps-symbolic")
        icon.set_pixel_size(24)
        box.append(icon)
        
        # Title
        title = Gtk.Label(label=__app_name__)
        title.add_css_class("title")
        box.append(title)
        
        return box
    
    def _create_menu(self):
        """Create the application menu."""
        menu = Gio.Menu()
        menu.append("About ZenScreen", "app.about")
        menu.append("Quit", "app.quit")
        return menu
    
    def _create_dashboard(self):
        """Create the main dashboard view."""
        # Scrolled window for the dashboard
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        
        # Main container
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        container.set_margin_start(24)
        container.set_margin_end(24)
        container.set_margin_top(24)
        container.set_margin_bottom(24)
        
        # Welcome section
        welcome = self._create_welcome_section()
        container.append(welcome)
        
        # Main stats row
        stats_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        stats_row.set_homogeneous(True)
        
        # Today's screen time card
        self.screen_time_card = self._create_screen_time_card()
        stats_row.append(self.screen_time_card)
        
        # Quick stats
        self.quick_stats_card = self._create_quick_stats_card()
        stats_row.append(self.quick_stats_card)
        
        container.append(stats_row)
        
        # App usage section with donut chart
        apps_label = Gtk.Label(label="Screen Time by App")
        apps_label.add_css_class("title-small")
        apps_label.set_halign(Gtk.Align.START)
        container.append(apps_label)
        
        # Donut chart card
        self.donut_card = self._create_donut_chart_card()
        self.donut_card.add_css_class("fade-in")
        container.append(self.donut_card)
        
        # App usage list (detailed times)
        self.apps_list_box = self._create_apps_list()
        self.apps_list_box.add_css_class("fade-in")
        container.append(self.apps_list_box)
        
        # Weekly overview section
        week_label = Gtk.Label(label="This Week")
        week_label.add_css_class("title-small")
        week_label.set_halign(Gtk.Align.START)
        container.append(week_label)
        
        self.week_chart = self._create_week_chart()
        container.append(self.week_chart)
        
        # Focus mode section
        focus_label = Gtk.Label(label="Focus Mode")
        focus_label.add_css_class("title-small")
        focus_label.set_halign(Gtk.Align.START)
        container.append(focus_label)
        
        self.focus_card = self._create_focus_card()
        container.append(self.focus_card)
        
        scrolled.set_child(container)
        return scrolled
    
    def _create_welcome_section(self):
        """Create the welcome/greeting section."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        
        # Time-based greeting
        hour = datetime.now().hour
        if hour < 12:
            greeting = "Good Morning"
            emoji = "🌅"
        elif hour < 17:
            greeting = "Good Afternoon"
            emoji = "☀️"
        elif hour < 21:
            greeting = "Good Evening"
            emoji = "🌆"
        else:
            greeting = "Good Night"
            emoji = "🌙"
        
        greeting_label = Gtk.Label(label=f"{emoji} {greeting}!")
        greeting_label.add_css_class("title-large")
        greeting_label.set_halign(Gtk.Align.START)
        box.append(greeting_label)
        
        date_label = Gtk.Label(label=date.today().strftime("%A, %B %d, %Y"))
        date_label.add_css_class("dim-label")
        date_label.set_halign(Gtk.Align.START)
        box.append(date_label)
        
        return box
    
    def _create_screen_time_card(self):
        """Create the main screen time display card."""
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        card.add_css_class("card")
        card.add_css_class("stat-card")
        card.set_valign(Gtk.Align.START)
        
        # Title
        title = Gtk.Label(label="Today's Screen Time")
        title.set_halign(Gtk.Align.START)
        card.append(title)
        
        # Time display
        self.time_label = Gtk.Label(label="0h 0m")
        self.time_label.add_css_class("value-large")
        self.time_label.set_halign(Gtk.Align.START)
        card.append(self.time_label)
        
        # Goal progress (clickable)
        goal_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        goal_box.set_valign(Gtk.Align.CENTER)
        
        self.goal_label = Gtk.Label(label="of 8h goal")
        self.goal_label.add_css_class("dim-label")
        goal_box.append(self.goal_label)
        
        # Edit goal button
        edit_goal_btn = Gtk.Button()
        edit_goal_btn.set_icon_name("document-edit-symbolic")
        edit_goal_btn.add_css_class("flat")
        edit_goal_btn.add_css_class("circular")
        edit_goal_btn.set_tooltip_text("Edit daily goal")
        edit_goal_btn.connect("clicked", self._on_edit_goal)
        goal_box.append(edit_goal_btn)
        
        card.append(goal_box)
        
        # Progress bar
        self.time_progress = Gtk.ProgressBar()
        self.time_progress.set_fraction(0)
        card.append(self.time_progress)
        
        return card
    
    def _create_quick_stats_card(self):
        """Create quick stats card."""
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        card.add_css_class("card")
        card.set_valign(Gtk.Align.START)
        
        # Title
        title = Gtk.Label(label="Quick Stats")
        title.add_css_class("title-small")
        title.set_halign(Gtk.Align.START)
        card.append(title)
        
        # Stats grid
        grid = Gtk.Grid()
        grid.set_row_spacing(16)
        grid.set_column_spacing(24)
        
        # Apps count
        apps_icon = Gtk.Image.new_from_icon_name("application-x-executable-symbolic")
        apps_icon.set_pixel_size(24)
        grid.attach(apps_icon, 0, 0, 1, 1)
        
        self.apps_count_label = Gtk.Label(label="0")
        self.apps_count_label.add_css_class("value-medium")
        grid.attach(self.apps_count_label, 1, 0, 1, 1)
        
        apps_desc = Gtk.Label(label="Apps used")
        apps_desc.add_css_class("dim-label")
        grid.attach(apps_desc, 2, 0, 1, 1)
        
        # Sessions count
        session_icon = Gtk.Image.new_from_icon_name("view-list-symbolic")
        session_icon.set_pixel_size(24)
        grid.attach(session_icon, 0, 1, 1, 1)
        
        self.sessions_label = Gtk.Label(label="0")
        self.sessions_label.add_css_class("value-medium")
        grid.attach(self.sessions_label, 1, 1, 1, 1)
        
        sessions_desc = Gtk.Label(label="Sessions")
        sessions_desc.add_css_class("dim-label")
        grid.attach(sessions_desc, 2, 1, 1, 1)
        
        # Productivity
        prod_icon = Gtk.Image.new_from_icon_name("starred-symbolic")
        prod_icon.set_pixel_size(24)
        grid.attach(prod_icon, 0, 2, 1, 1)
        
        self.productivity_label = Gtk.Label(label="0%")
        self.productivity_label.add_css_class("value-medium")
        grid.attach(self.productivity_label, 1, 2, 1, 1)
        
        prod_desc = Gtk.Label(label="Productivity")
        prod_desc.add_css_class("dim-label")
        grid.attach(prod_desc, 2, 2, 1, 1)
        
        card.append(grid)
        
        return card
    
    def _create_donut_chart_card(self):
        """Create the donut chart card with legend."""
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        card.add_css_class("card")
        card.add_css_class("donut-card")
        
        # Donut chart
        self.donut_chart = DonutChartWidget()
        self.donut_chart.set_halign(Gtk.Align.CENTER)
        self.donut_chart.set_valign(Gtk.Align.CENTER)
        card.append(self.donut_chart)
        
        # Legend container
        legend_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        legend_box.set_hexpand(True)
        legend_box.set_valign(Gtk.Align.CENTER)
        
        self.legend_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        legend_box.append(self.legend_container)
        
        card.append(legend_box)
        
        return card
    
    def _create_legend_item(self, app_name: str, duration: str, color_index: int):
        """Create a legend item with colored indicator."""
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.add_css_class("app-legend-item")
        
        # Color indicator
        color = CHART_COLORS[color_index % len(CHART_COLORS)]
        color_box = Gtk.DrawingArea()
        color_box.set_size_request(12, 12)
        color_box.set_valign(Gtk.Align.CENTER)
        
        def draw_color(area, cr, width, height):
            cr.set_source_rgb(*color)
            cr.arc(width / 2, height / 2, min(width, height) / 2, 0, 2 * 3.14159)
            cr.fill()
        
        color_box.set_draw_func(draw_color)
        row.append(color_box)
        
        # App name
        name_label = Gtk.Label(label=self._normalize_app_name(app_name))
        name_label.set_halign(Gtk.Align.START)
        name_label.set_hexpand(True)
        name_label.add_css_class("heading")
        row.append(name_label)
        
        # Duration
        time_label = Gtk.Label(label=duration)
        time_label.add_css_class("dim-label")
        row.append(time_label)
        
        return row
    
    def _create_category_legend_item(self, category_name: str, duration: str, color: tuple, icon_name: str):
        """Create a legend item for a category with icon and custom color."""
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.add_css_class("app-legend-item")
        
        # Color indicator
        color_box = Gtk.DrawingArea()
        color_box.set_size_request(12, 12)
        color_box.set_valign(Gtk.Align.CENTER)
        
        def draw_color(area, cr, width, height):
            cr.set_source_rgb(*color)
            cr.arc(width / 2, height / 2, min(width, height) / 2, 0, 2 * 3.14159)
            cr.fill()
        
        color_box.set_draw_func(draw_color)
        row.append(color_box)
        
        # Icon
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(16)
        row.append(icon)
        
        # Category name
        name_label = Gtk.Label(label=category_name)
        name_label.set_halign(Gtk.Align.START)
        name_label.set_hexpand(True)
        name_label.add_css_class("heading")
        row.append(name_label)
        
        # Duration
        time_label = Gtk.Label(label=duration)
        time_label.add_css_class("dim-label")
        row.append(time_label)
        
        return row
    
    def _normalize_app_name(self, app_name: str) -> str:
        """Normalize app names to be more human-readable."""
        if not app_name:
            return "Desktop"
        
        # Common app name mappings
        app_mappings = {
            # Browsers
            "google-chrome": "Chrome",
            "google-chrome-stable": "Chrome",
            "chrome": "Chrome",
            "chromium": "Chromium",
            "chromium-browser": "Chromium",
            "firefox": "Firefox",
            "firefox-esr": "Firefox",
            "org.mozilla.firefox": "Firefox",
            "brave": "Brave",
            "brave-browser": "Brave",
            "microsoft-edge": "Edge",
            "tradingview": "TradingView",
            "electron": "Electron App",
            
            # Code editors
            "code": "VS Code",
            "code-oss": "VS Code",
            "visual studio code": "VS Code",
            "cursor": "Cursor",
            "antigravity": "Antigravity",  # Added
            "sublime_text": "Sublime Text",
            "atom": "Atom",
            "vim": "Vim",
            "neovim": "Neovim",
            "emacs": "Emacs",
            
            # Terminals
            "gnome-terminal": "Terminal",
            "org.gnome.terminal": "Terminal",
            "konsole": "Konsole",
            "alacritty": "Alacritty",
            "kitty": "Kitty",
            "tilix": "Tilix",
            "terminator": "Terminator",
            "warp": "Warp",
            
            # File managers
            "nautilus": "Files",
            "org.gnome.nautilus": "Files",
            "dolphin": "Dolphin",
            "thunar": "Thunar",
            "nemo": "Nemo",
            
            # Communication
            "slack": "Slack",
            "discord": "Discord",
            "telegram-desktop": "Telegram",
            "org.telegram.desktop": "Telegram",
            "signal": "Signal",
            "whatsapp": "WhatsApp",
            "teams": "Teams",
            "zoom": "Zoom",
            
            # Media
            "spotify": "Spotify",
            "vlc": "VLC",
            "mpv": "MPV",
            "totem": "Videos",
            "rhythmbox": "Music",
            
            # Productivity
            "thunderbird": "Thunderbird",
            "evolution": "Evolution",
            "libreoffice": "LibreOffice",
            "obsidian": "Obsidian",
            "notion": "Notion",
            "todoist": "Todoist",
            
            # Development
            "postman": "Postman",
            "insomnia": "Insomnia",
            "dbeaver": "DBeaver",
            "docker": "Docker",
            "jetbrains": "JetBrains",
            
            # System
            "gnome-settings": "Settings",
            "gnome-control-center": "Settings",
            "systemsettings": "Settings",
            
            # Our app
            "zenscreen": "ZenScreen",
            "zenscreen-gtk": "ZenScreen",
            
            # Editors
            "gedit": "Text Editor",
            "org.gnome.gedit": "Text Editor",
            "gnome-text-editor": "Text Editor",
            "kate": "Kate",
            
            # Viewers
            "evince": "Document Viewer",
            "org.gnome.evince": "Document Viewer",
            "eog": "Image Viewer",
            "org.gnome.eog": "Image Viewer",
            "loupe": "Image Viewer",
            
            # Graphics & Design
            "gimp": "GIMP",
            "inkscape": "Inkscape",
            "blender": "Blender",
            "krita": "Krita",
            "darktable": "Darktable",
            "rawtherapee": "RawTherapee",
            "figma": "Figma",
            "figma-linux": "Figma",
            "canva": "Canva",
            "photoshop": "Photoshop",
            "illustrator": "Illustrator",
            "premiere": "Premiere Pro",
            "aftereffects": "After Effects",
            "davinci": "DaVinci Resolve",
            "kdenlive": "Kdenlive",
            "openshot": "OpenShot",
            "pitivi": "Pitivi",
            "obs": "OBS Studio",
            "obs-studio": "OBS Studio",
            
            # Gaming
            "steam": "Steam",
            "lutris": "Lutris",
            "heroic": "Heroic Launcher",
            "legendary": "Legendary",
            "gamehub": "GameHub",
            "bottles": "Bottles",
            "protonup-qt": "ProtonUp-Qt",
            "minecraft": "Minecraft",
            "minecraft-launcher": "Minecraft",
            "league": "League of Legends",
            "valorant": "Valorant",
            "dota": "Dota 2",
            "csgo": "CS:GO",
            "retroarch": "RetroArch",
            
            # Social & Communication
            "whatsapp": "WhatsApp",
            "whatsapp-web": "WhatsApp",
            "messenger": "Messenger",
            "skype": "Skype",
            "viber": "Viber",
            "element": "Element",
            "matrix": "Matrix",
            "mattermost": "Mattermost",
            "rocketchat": "Rocket.Chat",
            "keybase": "Keybase",
            "wire": "Wire",
            "guilded": "Guilded",
            "mumble": "Mumble",
            "teamspeak": "TeamSpeak",
            
            # Finance & Trading
            "tradingview": "TradingView",
            "binance": "Binance",
            "coinbase": "Coinbase",
            "metamask": "MetaMask",
            "ledger": "Ledger Live",
            "gnucash": "GnuCash",
            "homebank": "HomeBank",
            "kmymoney": "KMyMoney",
            
            # Office & Productivity
            "libreoffice-writer": "Writer",
            "libreoffice-calc": "Calc",
            "libreoffice-impress": "Impress",
            "libreoffice-draw": "Draw",
            "libreoffice-base": "Base",
            "onlyoffice": "OnlyOffice",
            "wps": "WPS Office",
            "abiword": "AbiWord",
            "gnumeric": "Gnumeric",
            "calligra": "Calligra",
            "latex": "LaTeX",
            "texstudio": "TeXstudio",
            "texmaker": "Texmaker",
            "lyx": "LyX",
            "zotero": "Zotero",
            "mendeley": "Mendeley",
            "calibre": "Calibre",
            "okular": "Okular",
            "zathura": "Zathura",
            "mupdf": "MuPDF",
            "xournalpp": "Xournal++",
            "rnote": "Rnote",
            
            # Note-taking & Knowledge
            "obsidian": "Obsidian",
            "notion": "Notion",
            "joplin": "Joplin",
            "simplenote": "Simplenote",
            "standard-notes": "Standard Notes",
            "logseq": "Logseq",
            "roam": "Roam Research",
            "craft": "Craft",
            "bear": "Bear",
            "evernote": "Evernote",
            "onenote": "OneNote",
            "trilium": "Trilium",
            "zettlr": "Zettlr",
            "marktext": "Mark Text",
            "typora": "Typora",
            "ghostwriter": "Ghostwriter",
            
            # Development & IDEs
            "pycharm": "PyCharm",
            "intellij": "IntelliJ IDEA",
            "webstorm": "WebStorm",
            "phpstorm": "PhpStorm",
            "goland": "GoLand",
            "rider": "Rider",
            "clion": "CLion",
            "datagrip": "DataGrip",
            "rubymine": "RubyMine",
            "android-studio": "Android Studio",
            "xcode": "Xcode",
            "eclipse": "Eclipse",
            "netbeans": "NetBeans",
            "codeblocks": "Code::Blocks",
            "geany": "Geany",
            "kdevelop": "KDevelop",
            "qtcreator": "Qt Creator",
            "monodevelop": "MonoDevelop",
            "brackets": "Brackets",
            "fleet": "Fleet",
            "zed": "Zed",
            "helix": "Helix",
            "lapce": "Lapce",
            
            # DevOps & Tools
            "docker": "Docker",
            "docker-desktop": "Docker Desktop",
            "podman": "Podman",
            "kubernetes": "Kubernetes",
            "lens": "Lens",
            "portainer": "Portainer",
            "github-desktop": "GitHub Desktop",
            "gitkraken": "GitKraken",
            "sourcetree": "Sourcetree",
            "sublime-merge": "Sublime Merge",
            "lazygit": "Lazygit",
            "tig": "Tig",
            "kubectl": "kubectl",
            "terraform": "Terraform",
            "ansible": "Ansible",
            "vagrant": "Vagrant",
            "virtualbox": "VirtualBox",
            "vmware": "VMware",
            "qemu": "QEMU",
            "gnome-boxes": "Boxes",
            "virt-manager": "Virt Manager",
            
            # Databases
            "pgadmin": "pgAdmin",
            "mysql-workbench": "MySQL Workbench",
            "mongodb-compass": "MongoDB Compass",
            "robo3t": "Robo 3T",
            "redis-insight": "RedisInsight",
            "beekeeper": "Beekeeper Studio",
            "dataflare": "DataFlare",
            "dbgate": "DbGate",
            "azuredatastudio": "Azure Data Studio",
            
            # Browsers (additional)
            "vivaldi": "Vivaldi",
            "opera": "Opera",
            "opera-gx": "Opera GX",
            "librewolf": "LibreWolf",
            "waterfox": "Waterfox",
            "tor-browser": "Tor Browser",
            "min": "Min Browser",
            "qutebrowser": "qutebrowser",
            "nyxt": "Nyxt",
            "epiphany": "GNOME Web",
            "falkon": "Falkon",
            "midori": "Midori",
            
            # Media Players (additional)
            "clementine": "Clementine",
            "strawberry": "Strawberry",
            "audacious": "Audacious",
            "lollypop": "Lollypop",
            "elisa": "Elisa",
            "gnome-music": "GNOME Music",
            "audacity": "Audacity",
            "ardour": "Ardour",
            "lmms": "LMMS",
            "hydrogen": "Hydrogen",
            "musescore": "MuseScore",
            "soundconverter": "SoundConverter",
            "handbrake": "HandBrake",
            "makemkv": "MakeMKV",
            "subtitleedit": "Subtitle Edit",
            "celluloid": "Celluloid",
            "haruna": "Haruna",
            
            # Streaming & Entertainment
            "netflix": "Netflix",
            "youtube": "YouTube",
            "youtube-music": "YouTube Music",
            "amazon-prime": "Prime Video",
            "disney-plus": "Disney+",
            "hbo-max": "HBO Max",
            "hulu": "Hulu",
            "twitch": "Twitch",
            "streamlabs": "Streamlabs",
            "plex": "Plex",
            "jellyfin": "Jellyfin",
            "kodi": "Kodi",
            "stremio": "Stremio",
            "popcorntime": "Popcorn Time",
            
            # System & Utilities
            "gnome-system-monitor": "System Monitor",
            "gnome-disks": "Disks",
            "gnome-tweaks": "GNOME Tweaks",
            "dconf-editor": "dconf Editor",
            "gparted": "GParted",
            "baobab": "Disk Usage Analyzer",
            "gnome-logs": "Logs",
            "gnome-calculator": "Calculator",
            "gnome-calendar": "Calendar",
            "gnome-contacts": "Contacts",
            "gnome-clocks": "Clocks",
            "gnome-weather": "Weather",
            "gnome-maps": "Maps",
            "gnome-photos": "Photos",
            "gnome-screenshot": "Screenshot",
            "flameshot": "Flameshot",
            "spectacle": "Spectacle",
            "shutter": "Shutter",
            "peek": "Peek",
            "ksnip": "Ksnip",
            "cheese": "Cheese",
            "simple-scan": "Document Scanner",
            "transmission": "Transmission",
            "qbittorrent": "qBittorrent",
            "deluge": "Deluge",
            "fragments": "Fragments",
            "syncthing": "Syncthing",
            "rclone": "Rclone",
            "restic": "Restic",
            "timeshift": "Timeshift",
            "deja-dup": "Backups",
            "seahorse": "Passwords & Keys",
            "keepassxc": "KeePassXC",
            "bitwarden": "Bitwarden",
            "1password": "1Password",
            "lastpass": "LastPass",
            "authy": "Authy",
            
            # Electron Apps (common)
            "electron": "Electron App",
            "nativefier": "Nativefier App",
        }
        
        # Special cases
        lower_name = app_name.lower().strip()
        
        # Handle "Unknown" - likely GNOME Shell or desktop interaction
        if lower_name == "unknown" or lower_name == "":
            return "Desktop"
        
        # Direct match
        if lower_name in app_mappings:
            return app_mappings[lower_name]
        
        # Try partial matches (for things like "google-chrome-stable")
        for pattern, friendly_name in app_mappings.items():
            if pattern in lower_name:
                return friendly_name
        
        # Clean up the name - capitalize first letter of each word
        # Remove common prefixes
        cleaned = app_name
        for prefix in ['org.', 'com.', 'io.', 'net.', 'app.']:
            if lower_name.startswith(prefix):
                cleaned = cleaned[len(prefix):]
        
        # Replace separators and capitalize
        cleaned = cleaned.replace('-', ' ').replace('_', ' ').replace('.', ' ')
        
        # Handle camelCase and PascalCase
        result = ""
        for i, char in enumerate(cleaned):
            if char.isupper() and i > 0 and cleaned[i-1].islower():
                result += " "
            result += char
        
        return result.title().strip() if result.strip() else "App"
    
    def _get_app_category(self, app_name: str) -> dict:
        """Get the category for an app."""
        lower_name = app_name.lower().strip() if app_name else ""
        normalized = self._normalize_app_name(app_name).lower()
        
        # Category definitions with colors
        categories = {
            "Productivity": {
                "color": (0.34, 0.74, 0.45),  # Green
                "icon": "starred-symbolic",
                "apps": ["vs code", "code", "antigravity", "cursor", "sublime", "atom", 
                         "vim", "neovim", "emacs", "libreoffice", "obsidian", "notion",
                         "todoist", "postman", "insomnia", "dbeaver", "jetbrains",
                         "pycharm", "intellij", "webstorm", "datagrip", "goland",
                         "terminal", "konsole", "alacritty", "kitty", "tilix", "warp",
                         "joplin", "logseq", "zettlr", "typora", "docker", "git",
                         "eclipse", "netbeans", "android studio", "xcode", "fleet",
                         "zed", "helix", "lapce", "geany", "texstudio", "latex",
                         "writer", "calc", "impress", "onlyoffice", "wps", "calibre"]
            },
            "Finance": {
                "color": (0.25, 0.85, 0.65),  # Teal
                "icon": "emblem-money-symbolic",
                "apps": ["tradingview", "binance", "coinbase", "metamask", "ledger",
                         "gnucash", "homebank", "kmymoney", "trading", "finance",
                         "crypto", "wallet", "bank", "stock", "invest"]
            },
            "Entertainment": {
                "color": (0.95, 0.45, 0.45),  # Red
                "icon": "applications-multimedia-symbolic",
                "apps": ["spotify", "vlc", "mpv", "totem", "rhythmbox", "music",
                         "youtube", "netflix", "twitch", "steam", "lutris", "games",
                         "video", "player", "plex", "jellyfin", "kodi", "stremio",
                         "disney", "hbo", "hulu", "prime video", "streaming",
                         "minecraft", "valorant", "dota", "league", "csgo", "gaming",
                         "heroic", "bottles", "retroarch"]
            },
            "Communication": {
                "color": (0.45, 0.65, 0.95),  # Blue
                "icon": "mail-unread-symbolic",
                "apps": ["slack", "discord", "telegram", "signal", "whatsapp", 
                         "teams", "zoom", "thunderbird", "evolution", "mail",
                         "messages", "skype", "messenger", "viber", "element",
                         "mattermost", "rocketchat", "keybase", "wire", "guilded"]
            },
            "Browsing": {
                "color": (0.95, 0.75, 0.25),  # Orange/Yellow
                "icon": "web-browser-symbolic",
                "apps": ["chrome", "chromium", "firefox", "brave", "edge", 
                         "safari", "opera", "browser", "vivaldi", "librewolf",
                         "waterfox", "tor", "epiphany", "falkon", "midori"]
            },
            "Design": {
                "color": (0.85, 0.45, 0.85),  # Purple
                "icon": "applications-graphics-symbolic",
                "apps": ["gimp", "inkscape", "blender", "krita", "figma", "canva",
                         "photoshop", "illustrator", "premiere", "aftereffects",
                         "davinci", "kdenlive", "openshot", "obs", "darktable"]
            },
            "System": {
                "color": (0.65, 0.65, 0.75),  # Gray
                "icon": "applications-system-symbolic",
                "apps": ["files", "nautilus", "dolphin", "thunar", "nemo",
                         "settings", "control", "desktop", "zenscreen", "gnome",
                         "system monitor", "disks", "tweaks", "gparted", "timeshift",
                         "calculator", "calendar", "clocks", "weather"]
            }
        }
        
        # Check which category the app belongs to
        for category, info in categories.items():
            for app_pattern in info["apps"]:
                if app_pattern in lower_name or app_pattern in normalized:
                    return {"name": category, "color": info["color"], "icon": info["icon"]}
        
        # Default category
        return {"name": "Other", "color": (0.5, 0.5, 0.6), "icon": "application-x-executable-symbolic"}
    
    def _group_apps_by_category(self, app_breakdown: list) -> list:
        """Group apps by category and sum their durations."""
        category_totals = {}
        category_apps = {}
        
        for app in app_breakdown:
            category = self._get_app_category(app['app_name'])
            cat_name = category['name']
            
            if cat_name not in category_totals:
                category_totals[cat_name] = {
                    'name': cat_name,
                    'color': category['color'],
                    'icon': category['icon'],
                    'duration': 0,
                    'apps': []
                }
            
            category_totals[cat_name]['duration'] += app['total_duration']
            category_totals[cat_name]['apps'].append({
                'name': self._normalize_app_name(app['app_name']),
                'duration': app['total_duration'],
                'formatted': app['formatted_duration']
            })
        
        # Sort by duration and format
        result = sorted(category_totals.values(), key=lambda x: x['duration'], reverse=True)
        
        # Add formatted duration
        for cat in result:
            hours = cat['duration'] // 3600
            minutes = (cat['duration'] % 3600) // 60
            if hours > 0:
                cat['formatted_duration'] = f"{hours}h {minutes}m"
            else:
                cat['formatted_duration'] = f"{minutes}m"
        
        return result
    
    def _create_apps_list(self):
        """Create the top applications list with clickable items."""
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card.add_css_class("card")
        
        # Title with view all button
        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        title = Gtk.Label(label="Top Apps")
        title.add_css_class("title-small")
        title.set_halign(Gtk.Align.START)
        title.set_hexpand(True)
        title_row.append(title)
        
        view_all_btn = Gtk.Button(label="View All")
        view_all_btn.add_css_class("flat")
        view_all_btn.connect("clicked", self._on_view_all_apps)
        title_row.append(view_all_btn)
        
        card.append(title_row)
        
        self.apps_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.append(self.apps_container)
        
        return card
    
    def _on_view_all_apps(self, button):
        """Show dialog with all apps used today."""
        dialog = Adw.Window(transient_for=self)
        dialog.set_title("All Apps Today")
        dialog.set_default_size(400, 500)
        dialog.set_modal(True)
        
        # Main content
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        # Header
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(True)
        main_box.append(header)
        
        # Scrolled list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        list_box.set_margin_start(16)
        list_box.set_margin_end(16)
        list_box.set_margin_top(16)
        list_box.set_margin_bottom(16)
        
        # Get all apps
        stats = self.app.stats.get_today_stats()
        
        if stats.app_breakdown:
            for app in stats.app_breakdown:
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
                row.set_margin_top(8)
                row.set_margin_bottom(8)
                
                # Category icon
                category = self._get_app_category(app['app_name'])
                icon = Gtk.Image.new_from_icon_name(category['icon'])
                icon.set_pixel_size(24)
                row.append(icon)
                
                # App name
                name = Gtk.Label(label=self._normalize_app_name(app['app_name']))
                name.set_halign(Gtk.Align.START)
                name.set_hexpand(True)
                row.append(name)
                
                # Category badge
                cat_label = Gtk.Label(label=category['name'])
                cat_label.add_css_class("dim-label")
                row.append(cat_label)
                
                # Duration
                time_label = Gtk.Label(label=app['formatted_duration'])
                time_label.add_css_class("heading")
                row.append(time_label)
                
                list_box.append(row)
        else:
            empty = Gtk.Label(label="No apps tracked yet")
            empty.add_css_class("dim-label")
            list_box.append(empty)
        
        scrolled.set_child(list_box)
        main_box.append(scrolled)
        
        dialog.set_content(main_box)
        dialog.present()
    
    def _create_app_row(self, name: str, duration: str, percentage: float, rank: int):
        """Create a single app usage row."""
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.set_margin_top(4)
        row.set_margin_bottom(4)
        
        # Rank badge
        rank_icons = ["🥇", "🥈", "🥉", "4", "5"]
        rank_text = rank_icons[rank - 1] if rank <= 5 else str(rank)
        rank_label = Gtk.Label(label=rank_text)
        rank_label.set_size_request(30, -1)
        row.append(rank_label)
        
        # App info
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        info_box.set_hexpand(True)
        
        name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        name_label = Gtk.Label(label=name)
        name_label.set_halign(Gtk.Align.START)
        name_label.add_css_class("heading")
        name_box.append(name_label)
        
        time_label = Gtk.Label(label=duration)
        time_label.add_css_class("dim-label")
        name_box.append(time_label)
        
        info_box.append(name_box)
        
        # Progress bar
        progress = Gtk.ProgressBar()
        progress.set_fraction(percentage / 100)
        progress.set_hexpand(True)
        info_box.append(progress)
        
        row.append(info_box)
        
        # Percentage
        pct_label = Gtk.Label(label=f"{percentage:.1f}%")
        pct_label.set_size_request(60, -1)
        row.append(pct_label)
        
        return row
    
    def _create_week_chart(self):
        """Create the weekly overview chart."""
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        card.add_css_class("card")
        
        # Chart container
        self.week_bars_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.week_bars_box.set_homogeneous(True)
        self.week_bars_box.set_valign(Gtk.Align.END)
        self.week_bars_box.set_size_request(-1, 150)
        
        card.append(self.week_bars_box)
        
        return card
    
    def _create_week_bar(self, day_name: str, duration_str: str, height_fraction: float, is_today: bool = False):
        """Create a single day bar for the week chart."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_valign(Gtk.Align.END)
        
        # Duration label
        dur_label = Gtk.Label(label=duration_str)
        dur_label.add_css_class("dim-label")
        dur_label.set_size_request(-1, 20)
        box.append(dur_label)
        
        # Bar
        bar = Gtk.Box()
        bar.add_css_class("week-bar-fill")
        if is_today:
            bar.add_css_class("suggested-action")
        height = max(10, int(100 * height_fraction))
        bar.set_size_request(-1, height)
        box.append(bar)
        
        # Day label
        day_label = Gtk.Label(label=day_name)
        if is_today:
            day_label.add_css_class("heading")
        else:
            day_label.add_css_class("dim-label")
        box.append(day_label)
        
        return box
    
    def _create_focus_card(self):
        """Create the focus mode card."""
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        card.add_css_class("card")
        
        # Info section
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        info_box.set_hexpand(True)
        
        title = Gtk.Label(label="🎯 Focus Mode")
        title.add_css_class("title-small")
        title.set_halign(Gtk.Align.START)
        info_box.append(title)
        
        self.focus_status_label = Gtk.Label(label="Start a focus session to minimize distractions")
        self.focus_status_label.add_css_class("dim-label")
        self.focus_status_label.set_halign(Gtk.Align.START)
        self.focus_status_label.set_wrap(True)
        info_box.append(self.focus_status_label)
        
        card.append(info_box)
        
        # Timer display (shown during active session)
        self.focus_timer_label = Gtk.Label(label="25:00")
        self.focus_timer_label.add_css_class("focus-timer")
        self.focus_timer_label.set_visible(False)
        card.append(self.focus_timer_label)
        
        # Buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        self.focus_start_button = Gtk.Button(label="Start Focus")
        self.focus_start_button.add_css_class("suggested-action")
        self.focus_start_button.connect("clicked", self._on_focus_start)
        button_box.append(self.focus_start_button)
        
        self.focus_stop_button = Gtk.Button(label="Stop")
        self.focus_stop_button.add_css_class("destructive-action")
        self.focus_stop_button.connect("clicked", self._on_focus_stop)
        self.focus_stop_button.set_visible(False)
        button_box.append(self.focus_stop_button)
        
        card.append(button_box)
        
        return card
    
    def update_stats(self):
        """Update all statistics displays."""
        try:
            stats = self.app.stats.get_today_stats()
            goal_seconds = int(self.app.db.get_setting('daily_goal_minutes', '480')) * 60
            
            # Update screen time
            self.time_label.set_label(stats.formatted_time)
            
            # Update progress
            progress = min(1.0, stats.total_screen_time / goal_seconds)
            self.time_progress.set_fraction(progress)
            
            # Update card color based on progress
            self.screen_time_card.remove_css_class("stat-card-green")
            self.screen_time_card.remove_css_class("stat-card-amber")
            self.screen_time_card.remove_css_class("stat-card-red")
            
            if progress < 0.5:
                self.screen_time_card.add_css_class("stat-card-green")
            elif progress < 0.8:
                pass  # Default purple
            elif progress < 1.0:
                self.screen_time_card.add_css_class("stat-card-amber")
            else:
                self.screen_time_card.add_css_class("stat-card-red")
            
            # Update quick stats
            self.apps_count_label.set_label(str(stats.unique_apps))
            self.sessions_label.set_label(str(stats.session_count))
            
            productivity = self.app.stats.get_productivity_score()
            self.productivity_label.set_label(f"{productivity['score']:.0f}%")
            
            # Update donut chart and legend with CATEGORIES
            if hasattr(self, 'donut_chart') and hasattr(self, 'legend_container'):
                # Group apps by category
                categories = self._group_apps_by_category(stats.app_breakdown)
                
                # Prepare data for chart
                chart_data = []
                for cat in categories:
                    chart_data.append({
                        'app_name': cat['name'],
                        'duration': cat['duration'],
                        'formatted_duration': cat['formatted_duration'],
                        'color': cat['color']
                    })
                
                # Update chart
                self.donut_chart.set_data(chart_data, stats.formatted_time)
                
                # Clear legend
                child = self.legend_container.get_first_child()
                while child:
                    next_child = child.get_next_sibling()
                    self.legend_container.remove(child)
                    child = next_child
                
                # Add category legend items
                for i, cat in enumerate(categories):
                    legend_item = self._create_category_legend_item(
                        cat['name'],
                        cat['formatted_duration'],
                        cat['color'],
                        cat['icon']
                    )
                    legend_item.add_css_class("slide-in")
                    self.legend_container.append(legend_item)
                
                if not categories:
                    empty = Gtk.Label(label="No activity yet")
                    empty.add_css_class("dim-label")
                    self.legend_container.append(empty)
            
            # Update apps list (separate detailed view)
            if hasattr(self, 'apps_container'):
                # Clear existing
                child = self.apps_container.get_first_child()
                while child:
                    next_child = child.get_next_sibling()
                    self.apps_container.remove(child)
                    child = next_child
                
                # Add new rows
                for i, app in enumerate(stats.app_breakdown[:5], 1):
                    row = self._create_app_row(
                        self._normalize_app_name(app['app_name']),
                        app['formatted_duration'],
                        app['percentage'],
                        i
                    )
                    row.add_css_class("slide-in")
                    self.apps_container.append(row)
                
                if not stats.app_breakdown:
                    empty = Gtk.Label(label="No activity recorded yet today")
                    empty.add_css_class("dim-label")
                    self.apps_container.append(empty)
            
            # Update week chart
            week_stats = self.app.stats.get_week_stats()
            
            # Clear existing bars
            child = self.week_bars_box.get_first_child()
            while child:
                next_child = child.get_next_sibling()
                self.week_bars_box.remove(child)
                child = next_child
            
            # Find max duration for scaling
            max_duration = max((d['total_duration'] for d in week_stats.days), default=1)
            
            today_str = date.today().isoformat()
            
            for day in week_stats.days:
                height = day['total_duration'] / max_duration if max_duration > 0 else 0
                bar = self._create_week_bar(
                    day['day_name'],
                    day['formatted_duration'] or '0m',
                    height,
                    is_today=(day['date'] == today_str)
                )
                self.week_bars_box.append(bar)
            
            # Update focus status
            focus_info = self.app.focus.get_session_info()
            if focus_info:
                self.focus_status_label.set_label("Focus session in progress...")
                self.focus_timer_label.set_label(focus_info['formatted_remaining'])
                self.focus_timer_label.set_visible(True)
                self.focus_start_button.set_visible(False)
                self.focus_stop_button.set_visible(True)
            else:
                self.focus_status_label.set_label("Start a focus session to minimize distractions")
                self.focus_timer_label.set_visible(False)
                self.focus_start_button.set_visible(True)
                self.focus_stop_button.set_visible(False)
            
        except Exception as e:
            print(f"Error updating stats: {e}")
    
    def _update_goal_display(self):
        """Update the goal label with current setting."""
        try:
            goal_hours = int(self.app.db.get_setting('daily_goal_minutes', '480')) // 60
            self.goal_label.set_label(f"of {goal_hours}h goal")
        except Exception:
            pass
    
    def _on_focus_start(self, button):
        """Start a focus session."""
        try:
            self.app.focus.start_session(duration_minutes=25)
            
            # Start timer update
            def update_timer():
                if not self.app.focus.is_active:
                    self.update_stats()
                    return False
                
                info = self.app.focus.get_session_info()
                if info:
                    self.focus_timer_label.set_label(info['formatted_remaining'])
                return True
            
            self.app._focus_timer_id = GLib.timeout_add(1000, update_timer)
            
            self.update_stats()
            
        except Exception as e:
            print(f"Error starting focus: {e}")
    
    def _on_focus_stop(self, button):
        """Stop the current focus session."""
        try:
            self.app.focus.stop_session(completed=False)
            
            if self.app._focus_timer_id:
                GLib.source_remove(self.app._focus_timer_id)
                self.app._focus_timer_id = None
            
            self.update_stats()
            
        except Exception as e:
            print(f"Error stopping focus: {e}")
    
    def _on_edit_goal(self, button):
        """Open dialog to edit daily screen time goal."""
        dialog = Adw.MessageDialog(transient_for=self)
        dialog.set_heading("Set Daily Goal")
        dialog.set_body("Set your target screen time limit for each day:")
        
        # Content box with spin button
        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        content.set_halign(Gtk.Align.CENTER)
        content.set_margin_top(16)
        content.set_margin_bottom(16)
        
        goal_spin = Gtk.SpinButton()
        goal_spin.set_range(1, 24)
        goal_spin.set_increments(1, 2)
        current_goal = int(self.app.db.get_setting('daily_goal_minutes', '480')) // 60
        goal_spin.set_value(current_goal)
        content.append(goal_spin)
        
        hours_label = Gtk.Label(label="hours per day")
        hours_label.add_css_class("dim-label")
        content.append(hours_label)
        
        dialog.set_extra_child(content)
        
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("save", "Save")
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("save")
        
        def on_response(dialog, response):
            if response == "save":
                new_goal = int(goal_spin.get_value())
                self.app.db.set_setting('daily_goal_minutes', str(new_goal * 60))
                # Update UI
                self.goal_label.set_label(f"of {new_goal}h goal")
                self.update_stats()
        
        dialog.connect("response", on_response)
        dialog.present()
    
    def _on_settings_clicked(self, button):
        """Open the settings dialog."""
        dialog = Adw.PreferencesWindow(transient_for=self)
        dialog.set_title("Settings")
        dialog.set_default_size(500, 600)
        
        # Create preferences page
        page = Adw.PreferencesPage()
        page.set_title("Settings")
        page.set_icon_name("emblem-system-symbolic")
        
        # Time Limits group
        limits_group = Adw.PreferencesGroup()
        limits_group.set_title("Time Limits")
        limits_group.set_description("Set daily screen time goals and reminders")
        
        # Daily goal
        goal_row = Adw.ActionRow()
        goal_row.set_title("Daily Screen Time Goal")
        goal_row.set_subtitle("Target hours per day (default: 8 hours)")
        
        goal_spin = Gtk.SpinButton()
        goal_spin.set_range(1, 24)
        goal_spin.set_increments(1, 2)
        current_goal = int(self.app.db.get_setting('daily_goal_minutes', '480')) // 60
        goal_spin.set_value(current_goal)
        goal_spin.set_valign(Gtk.Align.CENTER)
        goal_spin.connect("value-changed", lambda s: self._save_setting('daily_goal_minutes', str(int(s.get_value() * 60))))
        
        goal_label = Gtk.Label(label="hours")
        goal_label.add_css_class("dim-label")
        goal_label.set_margin_start(8)
        goal_label.set_valign(Gtk.Align.CENTER)
        
        goal_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        goal_box.append(goal_spin)
        goal_box.append(goal_label)
        goal_row.add_suffix(goal_box)
        
        limits_group.add(goal_row)
        
        # Break reminder interval
        break_row = Adw.ActionRow()
        break_row.set_title("Break Reminder Interval")
        break_row.set_subtitle("Minutes between break reminders")
        
        break_spin = Gtk.SpinButton()
        break_spin.set_range(15, 180)
        break_spin.set_increments(15, 30)
        current_break = int(self.app.db.get_setting('break_reminder_interval', '3600')) // 60
        break_spin.set_value(current_break)
        break_spin.set_valign(Gtk.Align.CENTER)
        break_spin.connect("value-changed", lambda s: self._save_setting('break_reminder_interval', str(int(s.get_value() * 60))))
        
        break_label = Gtk.Label(label="min")
        break_label.add_css_class("dim-label")
        break_label.set_margin_start(8)
        break_label.set_valign(Gtk.Align.CENTER)
        
        break_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        break_box.append(break_spin)
        break_box.append(break_label)
        break_row.add_suffix(break_box)
        
        limits_group.add(break_row)
        
        # Idle threshold
        idle_row = Adw.ActionRow()
        idle_row.set_title("Idle Threshold")
        idle_row.set_subtitle("Seconds before marking as idle")
        
        idle_spin = Gtk.SpinButton()
        idle_spin.set_range(60, 900)
        idle_spin.set_increments(30, 60)
        current_idle = int(self.app.db.get_setting('idle_threshold', '300'))
        idle_spin.set_value(current_idle)
        idle_spin.set_valign(Gtk.Align.CENTER)
        idle_spin.connect("value-changed", lambda s: self._save_setting('idle_threshold', str(int(s.get_value()))))
        
        idle_label = Gtk.Label(label="sec")
        idle_label.add_css_class("dim-label")
        idle_label.set_margin_start(8)
        idle_label.set_valign(Gtk.Align.CENTER)
        
        idle_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        idle_box.append(idle_spin)
        idle_box.append(idle_label)
        idle_row.add_suffix(idle_box)
        
        limits_group.add(idle_row)
        
        page.add(limits_group)
        
        # Notifications group
        notif_group = Adw.PreferencesGroup()
        notif_group.set_title("Notifications")
        
        # Enable notifications toggle
        notif_row = Adw.ActionRow()
        notif_row.set_title("Enable Notifications")
        notif_row.set_subtitle("Show desktop notifications for breaks and focus sessions")
        
        notif_switch = Gtk.Switch()
        notif_switch.set_active(self.app.db.get_setting('enable_notifications', 'true') == 'true')
        notif_switch.set_valign(Gtk.Align.CENTER)
        notif_switch.connect("notify::active", lambda s, _: self._save_setting('enable_notifications', 'true' if s.get_active() else 'false'))
        notif_row.add_suffix(notif_switch)
        notif_row.set_activatable_widget(notif_switch)
        
        notif_group.add(notif_row)
        
        page.add(notif_group)
        
        # Privacy group
        privacy_group = Adw.PreferencesGroup()
        privacy_group.set_title("Privacy")
        
        # Track window titles toggle
        titles_row = Adw.ActionRow()
        titles_row.set_title("Track Window Titles")
        titles_row.set_subtitle("Store window titles in database (may contain sensitive info)")
        
        titles_switch = Gtk.Switch()
        titles_switch.set_active(self.app.db.get_setting('track_window_titles', 'true') == 'true')
        titles_switch.set_valign(Gtk.Align.CENTER)
        titles_switch.connect("notify::active", lambda s, _: self._save_setting('track_window_titles', 'true' if s.get_active() else 'false'))
        titles_row.add_suffix(titles_switch)
        titles_row.set_activatable_widget(titles_switch)
        
        privacy_group.add(titles_row)
        
        page.add(privacy_group)
        
        dialog.add(page)
        dialog.present()
    
    def _save_setting(self, key: str, value: str):
        """Save a setting to the database."""
        try:
            self.app.db.set_setting(key, value)
        except Exception as e:
            print(f"Error saving setting: {e}")


def main():
    """Main entry point for the GUI application."""
    # Set the program name for window grouping and icon
    GLib.set_prgname(__app_id__)
    app = ZenScreenApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    main()
