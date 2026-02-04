"""Tests for database module."""

import pytest
from datetime import date, datetime
from pathlib import Path
import tempfile

from zenscreen.core.database import Database


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = Path(f.name)
    
    db = Database(db_path)
    yield db
    
    # Cleanup
    db_path.unlink(missing_ok=True)


def test_database_initialization(temp_db):
    """Test that database initializes correctly."""
    assert temp_db.db_path.exists()
    
    # Check default settings exist
    idle_threshold = temp_db.get_setting('idle_threshold')
    assert idle_threshold == '300'


def test_app_session_tracking(temp_db):
    """Test app session start and end."""
    session_id = temp_db.start_app_session('firefox', 'Example Page')
    assert isinstance(session_id, int)
    
    temp_db.end_app_session(session_id)
    
    # Check session was recorded
    usage = temp_db.get_usage_for_date(date.today())
    assert len(usage) == 1
    assert usage[0]['app_name'] == 'firefox'


def test_get_app_usage_summary(temp_db):
    """Test app usage summary."""
    # Create some test sessions
    s1 = temp_db.start_app_session('firefox', 'Page 1')
    temp_db.end_app_session(s1)
    
    s2 = temp_db.start_app_session('vscode', 'Code')
    temp_db.end_app_session(s2)
    
    summary = temp_db.get_app_usage_summary(date.today())
    assert len(summary) == 2
    app_names = [s['app_name'] for s in summary]
    assert 'firefox' in app_names
    assert 'vscode' in app_names


def test_settings(temp_db):
    """Test settings management."""
    temp_db.set_setting('test_key', 'test_value')
    value = temp_db.get_setting('test_key')
    assert value == 'test_value'
    
    all_settings = temp_db.get_all_settings()
    assert 'test_key' in all_settings


def test_focus_session(temp_db):
    """Test focus session tracking."""
    session_id = temp_db.start_focus_session(25, ['discord', 'firefox'])
    assert isinstance(session_id, int)
    
    active = temp_db.get_active_focus_session()
    assert active is not None
    assert active['id'] == session_id
    assert 'discord' in active['blocked_apps']
    
    temp_db.end_focus_session(session_id, completed=True)
    
    active = temp_db.get_active_focus_session()
    assert active is None
