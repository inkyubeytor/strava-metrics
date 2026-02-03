"""Cache management for Strava activity streams."""
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


CACHE_DIR = Path(".strava_cache")
CACHE_DIR.mkdir(exist_ok=True)

STREAMS_CACHE_FILE = CACHE_DIR / "activity_streams.json"
FAILED_CACHE_FILE = CACHE_DIR / "failed_activities.json"


def load_cache() -> tuple[Dict[int, Dict[str, Any]], set[int]]:
    """Load streams cache and failed activities from disk.
    
    Returns:
        Tuple of (streams_cache dict, failed_activities set)
    """
    streams_cache = {}
    failed_activities = set()
    
    if STREAMS_CACHE_FILE.exists():
        try:
            with open(STREAMS_CACHE_FILE, "r") as f:
                data = json.load(f)
                # Convert string keys back to integers
                streams_cache = {int(k): v for k, v in data.items()}
        except Exception as e:
            print(f"Error loading streams cache: {e}")
    
    if FAILED_CACHE_FILE.exists():
        try:
            with open(FAILED_CACHE_FILE, "r") as f:
                data = json.load(f)
                failed_activities = set(data.get("failed_ids", []))
        except Exception as e:
            print(f"Error loading failed activities cache: {e}")
    
    return streams_cache, failed_activities


def save_cache(streams_cache: Dict[int, Dict[str, Any]], failed_activities: set[int]) -> None:
    """Save streams cache and failed activities to disk.
    
    Args:
        streams_cache: Dictionary of activity_id -> stream data
        failed_activities: Set of activity IDs that failed to fetch
    """
    try:
        # Convert integer keys to strings for JSON serialization
        cache_data = {str(k): v for k, v in streams_cache.items()}
        with open(STREAMS_CACHE_FILE, "w") as f:
            json.dump(cache_data, f, indent=2)
    except Exception as e:
        print(f"Error saving streams cache: {e}")
    
    try:
        failed_data = {
            "failed_ids": sorted(list(failed_activities)),
            "last_updated": datetime.now().isoformat(),
        }
        with open(FAILED_CACHE_FILE, "w") as f:
            json.dump(failed_data, f, indent=2)
    except Exception as e:
        print(f"Error saving failed activities cache: {e}")


def get_cached_stream(activity_id: int, streams_cache: Dict[int, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Get cached stream data for an activity.
    
    Args:
        activity_id: The Strava activity ID
        streams_cache: The streams cache dictionary
        
    Returns:
        Stream data if cached, None otherwise
    """
    return streams_cache.get(activity_id)


def cache_stream(
    activity_id: int,
    stream_data: Dict[str, Any],
    streams_cache: Dict[int, Dict[str, Any]],
) -> None:
    """Cache stream data for an activity.
    
    Args:
        activity_id: The Strava activity ID
        stream_data: The stream data to cache
        streams_cache: The streams cache dictionary to update
    """
    streams_cache[activity_id] = stream_data


def mark_failed(activity_id: int, failed_activities: set[int]) -> None:
    """Mark an activity as failed to fetch.
    
    Args:
        activity_id: The Strava activity ID
        failed_activities: The set of failed activity IDs to update
    """
    failed_activities.add(activity_id)


def clear_failed(failed_activities: set[int]) -> None:
    """Clear the set of failed activities.
    
    Args:
        failed_activities: The set of failed activity IDs to clear
    """
    failed_activities.clear()


def clear_cache() -> None:
    """Clear all cache files from disk."""
    try:
        if STREAMS_CACHE_FILE.exists():
            STREAMS_CACHE_FILE.unlink()
        if FAILED_CACHE_FILE.exists():
            FAILED_CACHE_FILE.unlink()
    except Exception as e:
        print(f"Error clearing cache: {e}")
