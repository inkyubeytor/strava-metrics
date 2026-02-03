"""Strava API client for fetching athlete data."""
import polars as pl
import requests
from typing import List, Dict, Any
from datetime import datetime
from stream_cache import (
    load_cache,
    save_cache,
    get_cached_stream,
    cache_stream,
    mark_failed,
)


def format_pace(pace_min_mi: float) -> str:
    """Format pace from minutes to MM:SS format.
    
    Args:
        pace_min_mi: Pace in minutes per mile
        
    Returns:
        Formatted pace string like "7:30"
    """
    if pace_min_mi <= 0:
        return "0:00"
    minutes = int(pace_min_mi)
    seconds = int((pace_min_mi - minutes) * 60)
    return f"{minutes}:{seconds:02d}"


def format_time(seconds: int) -> str:
    """Format seconds to HH:MM:SS format.
    
    Args:
        seconds: Total seconds
        
    Returns:
        Formatted time string like "1:23:45"
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours}:{minutes:02d}:{secs:02d}"


class StravaAPIClient:
    """Client for interacting with Strava API."""

    def __init__(self, access_token: str):
        """Initialize Strava API client.
        
        Args:
            access_token: Valid Strava API access token
        """
        self.access_token = access_token
        from strava_auth import StravaAuth
        
        # Create a minimal StravaAuth instance just for API calls
        self.auth = StravaAuth("", "", "")
        self.auth.api_base_url = "https://www.strava.com/api/v3"
        
        # Load cache
        self.streams_cache, self.failed_activities = load_cache()

    def get_activities(self, per_page: int = 200) -> List[Dict[str, Any]]:
        """Fetch all athlete activities.
        
        Args:
            per_page: Number of activities to fetch per page (max 200)
            
        Returns:
            List of activity dictionaries
        """
        activities = []
        page = 1
        
        while True:
            response_data = self.auth.get_athlete_activities(
                self.access_token, per_page=per_page, page=page
            )
            
            if not response_data:
                break
                
            activities.extend(response_data)
            
            if len(response_data) < per_page:
                break
                
            page += 1
        
        return activities

    def get_athlete(self) -> Dict[str, Any]:
        """Get authenticated athlete's profile.
        
        Returns:
            Athlete information dictionary
        """
        return self.auth.get_athlete_info(self.access_token)

    def get_activity_streams(self, activity_id: int) -> Dict[str, Any]:
        """Get activity streams (time and distance) from Strava API.
        
        Args:
            activity_id: ID of the activity
            
        Returns:
            Dictionary with time and distance streams
        """
        headers = {"Authorization": f"Bearer {self.access_token}"}
        url = f"{self.auth.api_base_url}/activities/{activity_id}/streams?keys=time,distance&key_by_type=true"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def activities_to_dataframe(self, activities: List[Dict[str, Any]]) -> pl.DataFrame:
        """Convert activities list to polars DataFrame in miles.
        
        Args:
            activities: List of activity dictionaries from Strava API
            
        Returns:
            Polars DataFrame with activity data in miles
        """
        if not activities:
            return pl.DataFrame()
        
        data = []
        for activity in activities:
            pace_min_mi = (
                60 / (activity.get("average_speed", 1) * 2.237)
                if activity.get("average_speed", 0) > 0
                else 0
            )
            data.append({
                "Name": activity.get("name", ""),
                "Date": datetime.fromisoformat(activity.get("start_date_local", "")),
                "Type": activity.get("type", ""),
                "Distance (mi)": activity.get("distance", 0) / 1609.34,
                "Duration (min)": activity.get("moving_time", 0) / 60,
                "Elevation (ft)": activity.get("total_elevation_gain", 0) * 3.28084,
                "Avg Speed (mph)": activity.get("average_speed", 0) * 2.237,
                "Pace (min/mi)": pace_min_mi,
                "Pace (MM:SS)": format_pace(pace_min_mi),
                "Calories": activity.get("calories", 0),
                "HR": activity.get("average_heartrate", 0),
                "Activity ID": activity.get("id", 0),
            })
        
        return pl.DataFrame(data)

    def get_activity_timeseries(self, activity_id: int, force_refresh: bool = False) -> pl.DataFrame:
        """Get distance vs time timeseries for an activity from Strava Streams API.
        
        Uses local cache to avoid re-querying. Failed activities are not retried by default.
        
        Args:
            activity_id: ID of the activity
            force_refresh: If True, ignore cache and failed list, query API
            
        Returns:
            Polars DataFrame with time and distance (miles)
        """
        # Check if activity previously failed and not forcing refresh
        if activity_id in self.failed_activities and not force_refresh:
            return pl.DataFrame()
        
        # Check cache first (unless forcing refresh)
        if not force_refresh:
            cached = get_cached_stream(activity_id, self.streams_cache)
            if cached is not None:
                return self._parse_stream_to_dataframe(cached)
        
        try:
            streams = self.get_activity_streams(activity_id)
            
            # Extract time and distance streams
            time_data = streams.get("time", {}).get("data", [])
            distance_data = streams.get("distance", {}).get("data", [])
            
            if not time_data or not distance_data or len(time_data) != len(distance_data):
                mark_failed(activity_id, self.failed_activities)
                save_cache(self.streams_cache, self.failed_activities)
                return pl.DataFrame()
            
            # Cache the stream data
            cache_stream(activity_id, streams, self.streams_cache)
            save_cache(self.streams_cache, self.failed_activities)
            
            return self._parse_stream_to_dataframe(streams)
        except Exception as e:
            print(f"Error fetching streams for activity {activity_id}: {e}")
            mark_failed(activity_id, self.failed_activities)
            save_cache(self.streams_cache, self.failed_activities)
            return pl.DataFrame()
    
    def _parse_stream_to_dataframe(self, streams: Dict[str, Any]) -> pl.DataFrame:
        """Parse stream data into a Polars DataFrame.
        
        Args:
            streams: Stream data from Strava API
            
        Returns:
            Polars DataFrame with time and distance (miles)
        """
        time_data = streams.get("time", {}).get("data", [])
        distance_data = streams.get("distance", {}).get("data", [])
        
        if not time_data or not distance_data:
            return pl.DataFrame()
        
        # Convert meters to miles
        data = [
            {
                "elapsed_seconds": int(t),
                "distance_mi": d / 1609.34,
            }
            for t, d in zip(time_data, distance_data)
        ]
        
        return pl.DataFrame(data)

    def get_stats_summary(self, activities_df: pl.DataFrame) -> Dict[str, Any]:
        """Calculate summary statistics from activities in miles.
        
        Args:
            activities_df: Polars DataFrame of activities
            
        Returns:
            Dictionary with summary statistics
        """
        if activities_df.height == 0:
            return {
                "total_distance": 0,
                "total_duration": 0,
                "total_elevation": 0,
                "avg_pace": 0,
                "num_activities": 0,
            }
        
        return {
            "total_distance": activities_df["Distance (mi)"].sum(),
            "total_duration": activities_df["Duration (min)"].sum(),
            "total_elevation": activities_df["Elevation (ft)"].sum(),
            "avg_pace": activities_df["Pace (min/mi)"].mean(),
            "num_activities": activities_df.height,
            "avg_distance": activities_df["Distance (mi)"].mean(),
        }

    def get_time_and_distance_dataframes(self, activities: List[Dict[str, Any]]) -> tuple[pl.DataFrame, pl.DataFrame]:
        """Create time-indexed and distance-indexed dataframes across all runs.
        
        Time dataframe: sampled every second, records last distance before that second (in miles).
        Distance dataframe: sampled every 0.01 miles, records first time that distance is passed.
        
        Args:
            activities: List of activity dictionaries with Activity ID
            
        Returns:
            Tuple of (time_df, distance_df) with distances in miles
        """
        all_time_data = []
        all_distance_data = []
        
        for activity in activities:
            activity_id = int(activity.get("id", 0))
            ts = self.get_activity_timeseries(activity_id)
            
            if ts.height == 0:
                continue
            
            ts_sorted = ts.sort("elapsed_seconds")
            
            # TIME DATAFRAME: resample every second using forward fill
            time_resampled = (
                ts_sorted
                .with_columns(
                    (pl.col("elapsed_seconds") // 1).alias("second")
                )
                .group_by("second")
                .agg(pl.col("distance_mi").last())
                .sort("second")
                .with_columns(
                    pl.col("distance_mi").forward_fill()
                )
            )
            
            time_resampled = time_resampled.with_columns(
                pl.lit(activity_id).alias("activity_id")
            ).select(["activity_id", "second", "distance_mi"])
            
            all_time_data.append(time_resampled)
            
            # DISTANCE DATAFRAME: resample every 0.01 miles
            max_distance_mi = ts_sorted["distance_mi"].max()
            
            # Create mile intervals (every 0.01 miles) to match distance_mi column type
            mile_intervals = pl.DataFrame({
                "distance_mi": [i * 0.01 for i in range(0, int(max_distance_mi * 100) + 1)]
            })
            
            distance_resampled = (
                mile_intervals
                .join_asof(
                    ts_sorted.select(["distance_mi", "elapsed_seconds"]),
                    on="distance_mi",
                    strategy="forward"
                )
                .with_columns(
                    pl.lit(activity_id).alias("activity_id")
                )
                .select(["activity_id", "distance_mi", "elapsed_seconds"])
            )
            
            all_distance_data.append(distance_resampled)
        
        time_df = pl.concat(all_time_data) if all_time_data else pl.DataFrame()
        distance_df = pl.concat(all_distance_data) if all_distance_data else pl.DataFrame()
        
        return time_df, distance_df

    def compute_personal_best_times(self, activities: List[Dict[str, Any]]) -> pl.DataFrame:
        """Compute fastest time to achieve each distance using sliding window DP.
        
        Uses dynamic programming with sliding window approach to find the fastest time
        to cover any distance in any run, including sub-intervals that don't start at
        the beginning. Results are in miles.
        
        Args:
            activities: List of activity dictionaries with Activity ID
            
        Returns:
            Polars DataFrame with columns: distance_mi, pb_seconds, pb_pace_min_mi, pb_pace_mm_ss
        """
        all_pb_data = {}  # distance_mi -> min_seconds
        
        for activity in activities:
            activity_id = int(activity.get("id", 0))
            ts = self.get_activity_timeseries(activity_id)
            
            if ts.height == 0:
                continue
            
            ts_sorted = ts.sort("elapsed_seconds")
            
            # Extract data as lists for efficient sliding window
            distances = ts_sorted["distance_mi"].to_list()
            times = ts_sorted["elapsed_seconds"].to_list()
            
            if len(distances) < 2:
                continue
            
            # Sliding window approach: for each pair of points (i, j),
            # the distance covered is distances[j] - distances[i]
            # and the time taken is times[j] - times[i]
            for i in range(len(distances)):
                for j in range(i + 1, len(distances)):
                    distance_covered = round(distances[j] - distances[i], 2)
                    time_taken = times[j] - times[i]
                    
                    # Skip if distance is 0 or very small (less than 0.01 miles)
                    if distance_covered <= 0.01:
                        continue
                    
                    # Update PB if this is faster (or first entry for this distance)
                    if distance_covered not in all_pb_data or time_taken < all_pb_data[distance_covered]:
                        all_pb_data[distance_covered] = time_taken
        
        # Convert to DataFrame with pace calculations
        pb_records = [
            {
                "distance_mi": d,
                "pb_seconds": t,
                "pb_pace_min_mi": (t / 60) / d if d > 0 else 0,
                "pb_pace_mm_ss": format_pace((t / 60) / d) if d > 0 else "0:00",
                "pb_time_hhmmss": format_time(int(t)),
            }
            for d, t in sorted(all_pb_data.items())
        ]
        
        return pl.DataFrame(pb_records) if pb_records else pl.DataFrame()


