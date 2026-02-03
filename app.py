import streamlit as st
import polars as pl
import requests
import plotly.graph_objects as go
from dotenv import load_dotenv
from strava_auth import (
    load_strava_auth,
    is_authenticated,
    save_token_to_session,
    logout,
)
from strava_api import StravaAPIClient

# Load environment variables
load_dotenv()


def format_time(seconds: int) -> str:
    """Format seconds to HH:MM:SS format."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours}:{minutes:02d}:{secs:02d}"


def generate_run_names(activities_df: pl.DataFrame) -> dict:
    """Generate run names with ISO 8601 dates and index for duplicates.
    
    Args:
        activities_df: DataFrame with activities
        
    Returns:
        Dictionary mapping activity_id to run name
    """
    # Group by date and count
    date_counts = activities_df.group_by(pl.col("Date").cast(pl.Date)).agg(
        pl.col("Activity ID").count().alias("count")
    )
    
    dates_with_multiples = set(
        date_counts.filter(pl.col("count") > 1)["Date"].to_list()
    )
    
    run_names = {}
    date_index_map = {}
    
    for row in activities_df.sort("Date").iter_rows(named=True):
        activity_id = int(row["Activity ID"])
        date = row["Date"].date()
        
        if date not in date_index_map:
            date_index_map[date] = 0
        
        date_index_map[date] += 1
        
        if date in dates_with_multiples:
            run_names[activity_id] = f"{date} #{date_index_map[date]}"
        else:
            run_names[activity_id] = str(date)
    
    return run_names


# Set page configuration
st.set_page_config(
    page_title="Strava Metrics Dashboard",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state
if "is_authenticated" not in st.session_state:
    st.session_state.is_authenticated = False
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = None


def handle_oauth_callback():
    """Handle OAuth callback from URL parameters."""
    try:
        query_params = st.query_params
        if "code" in query_params:
            code = query_params["code"]
            
            # Exchange code for token
            auth = load_strava_auth()
            token_response = auth.exchange_code_for_token(code)
            save_token_to_session(token_response)
            
            # Clean up URL
            st.query_params.clear()
            st.success("✅ Successfully authenticated with Strava!")
            st.rerun()
    except Exception as e:
        st.error(f"❌ Authentication failed: {str(e)}")


# Check for OAuth callback
handle_oauth_callback()

# Title
st.title("🏃 Strava Metrics Dashboard")
st.markdown("---")

# Sidebar with authentication
with st.sidebar:
    st.header("🔐 Authentication")
    
    if is_authenticated():
        try:
            # Get athlete info
            client = StravaAPIClient(st.session_state.access_token)
            athlete = client.get_athlete()
            
            st.success(f"✅ Logged in as {athlete.get('firstname')} {athlete.get('lastname')}")
            st.caption(f"City: {athlete.get('city', 'N/A')}")
            
            if st.button("🚪 Logout"):
                logout()
                st.rerun()
                
        except Exception as e:
            st.warning(f"⚠️ Error fetching profile: {str(e)}")
            if st.button("Logout"):
                logout()
                st.rerun()
    else:
        st.info("👋 Not authenticated with Strava")
        
        try:
            auth = load_strava_auth()
            auth_url = auth.get_auth_url()
            st.markdown(
                f"[🔗 Click here to connect with Strava]({auth_url})",
                unsafe_allow_html=False,
            )
        except ValueError as e:
            st.error(f"❌ Configuration error: {str(e)}")
            st.info(
                """
                To use this dashboard:
                1. Go to https://www.strava.com/settings/api
                2. Create an OAuth application
                3. Create a `.env` file with:
                   - STRAVA_CLIENT_ID=your_id
                   - STRAVA_CLIENT_SECRET=your_secret
                """
            )

if is_authenticated():
    st.markdown("---")
    
    # Fetch and display data
    try:
        client = StravaAPIClient(st.session_state.access_token)
        
        # Add refresh buttons in sidebar
        with st.sidebar:
            st.header("🔄 Refresh Data")
            
            col_refresh1, col_refresh2 = st.columns(2)
            with col_refresh1:
                if st.button("📥 Pull New Activities"):
                    st.session_state.refresh_all = True
                    st.rerun()
            
            with col_refresh2:
                if st.button("🔁 Refresh Existing"):
                    st.session_state.refresh_existing = True
                    st.rerun()
        
        # Check for refresh flags
        refresh_all = st.session_state.get("refresh_all", False)
        refresh_existing = st.session_state.get("refresh_existing", False)
        
        with st.spinner("📊 Fetching your Strava activities..."):
            activities = client.get_activities()
            activities_df = client.activities_to_dataframe(activities)
            
            if refresh_all or refresh_existing:
                # Refresh all activity streams
                from stream_cache import clear_failed
                
                if refresh_all:
                    st.info("Refreshing all activity streams...")
                    clear_failed(client.failed_activities)
                else:
                    st.info("Refreshing existing activity streams...")
                
                for activity_id in activities_df["Activity ID"].to_list():
                    client.get_activity_timeseries(int(activity_id), force_refresh=True)
                
                # Clear refresh flags
                st.session_state.refresh_all = False
                st.session_state.refresh_existing = False
                st.success("✅ Activity streams refreshed!")
        
        if activities_df.height == 0:
            st.info("No activities found. Start logging some activities on Strava!")
        else:
            # Date range filter
            with st.sidebar:
                st.header("📅 Dashboard Settings")
                min_date = activities_df["Date"].min().date()
                max_date = activities_df["Date"].max().date()
                
                date_range = st.date_input(
                    "Select date range",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date,
                )
            
            # Filter data
            filtered_df = activities_df.filter(
                (pl.col("Date").cast(pl.Date) >= date_range[0])
                & (pl.col("Date").cast(pl.Date) <= date_range[1])
            )
            
            # Filter to only runs
            filtered_df = filtered_df.filter(pl.col("Type") == "Run")
            
            # Calculate statistics
            stats = client.get_stats_summary(filtered_df)
            
            # Metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Total Distance",
                    f"{stats['total_distance']:.1f} mi",
                    f"{stats['num_activities']} activities",
                )
            
            with col2:
                hours = int(stats["total_duration"] // 60)
                minutes = int(stats["total_duration"] % 60)
                st.metric("Total Time", f"{hours}h {minutes}m")
            
            with col3:
                st.metric(
                    "Avg Pace",
                    f"{stats['avg_pace']:.2f} min/mi",
                    f"{stats['total_elevation']:.0f}ft elevation",
                )
            
            with col4:
                st.metric("Activities", f"{stats['num_activities']}")
            
            st.markdown("---")
            
            # Recent activities table with timeseries view
            st.subheader("📋 Recent Activities")
            display_cols = ["Name", "Date", "Type", "Distance (mi)", "Duration (min)", "Avg Speed (mph)", "Elevation (ft)"]
            display_df = filtered_df.select(display_cols).sort("Date", descending=True)
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            
            # Timeseries view
            
            st.markdown("---")
            
            # Charts
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📈 Distance Over Time")
                daily_distance = (
                    filtered_df.select("Date", "Distance (mi)")
                    .group_by("Date")
                    .agg(pl.col("Distance (mi)").sum())
                    .sort("Date")
                )
                st.line_chart(daily_distance.to_pandas().set_index("Date"))
            
            with col2:
                st.subheader("⏱️ Pace Trends")
                daily_pace = (
                    filtered_df.select("Date", "Pace (min/mi)")
                    .group_by("Date")
                    .agg(pl.col("Pace (min/mi)").mean())
                    .sort("Date")
                )
                st.line_chart(daily_pace.to_pandas().set_index("Date"))
            
            col3, col4 = st.columns(2)
            
            with col3:
                st.subheader("⏳ Activity Duration")
                daily_duration = (
                    filtered_df.select("Date", "Duration (min)")
                    .group_by("Date")
                    .agg(pl.col("Duration (min)").sum())
                    .sort("Date")
                )
                st.bar_chart(daily_duration.to_pandas().set_index("Date"))
            
            with col4:
                st.subheader("🏔️ Elevation Gain")
                daily_elevation = (
                    filtered_df.select("Date", "Elevation (ft)")
                    .group_by("Date")
                    .agg(pl.col("Elevation (ft)").sum())
                    .sort("Date")
                )
                st.area_chart(daily_elevation.to_pandas().set_index("Date"))
            
            st.markdown("---")
            
            # Aggregate time and distance curves
            st.subheader("📊 All Activities - Time Series")
            
            with st.spinner("📈 Processing time and distance series..."):
                time_df, distance_df = client.get_time_and_distance_dataframes(activities)
            
            if time_df.height > 0:
                # Plot time-indexed curves with Plotly
                fig = go.Figure()
                
                # Group by activity and plot
                for activity_id in time_df["activity_id"].unique().to_list():
                    activity_data = time_df.filter(pl.col("activity_id") == activity_id).sort("second")
                    
                    # Calculate deviation from linear pace
                    seconds = activity_data["second"].to_list()
                    distances = activity_data["distance_mi"].to_list()
                    
                    if len(seconds) > 1 and distances[-1] > 0:
                        # Linear distance-time relationship
                        avg_pace = distances[-1] / seconds[-1]  # miles per second
                        linear_distances = [s * avg_pace for s in seconds]
                        
                        # Deviation from linear
                        deviations = [d - linear_d for d, linear_d in zip(distances, linear_distances)]
                        
                        fig.add_trace(go.Scatter(
                            x=seconds,
                            y=deviations,
                            mode="lines",
                            name=f"Run {activity_id}",
                            opacity=0.7,
                            hovertemplate="<b>Time:</b> %{x}s<br><b>Deviation:</b> %{y:.3f} mi<extra></extra>"
                        ))
                
                fig.update_layout(
                    title="Distance-Time Curve Deviation from Linear Pace",
                    xaxis_title="Time (seconds)",
                    yaxis_title="Deviation from Expected Distance (miles)",
                    hovermode="x unified",
                    height=600,
                    template="plotly_white"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            
            # Distance over time scatter plot
            st.subheader("📍 Distance Over Time - Scatter")
            
            fig = go.Figure()
            
            # Collect all data for scatter plot
            dates = []
            distances = []
            names = []
            
            for activity_id in activities_df["Activity ID"].to_list():
                activity_info = activities_df.filter(pl.col("Activity ID") == activity_id)
                if activity_info.height > 0:
                    dates.append(activity_info[0]["Date"][0])
                    distances.append(activity_info[0]["Distance (mi)"][0])
                    names.append(activity_info[0]["Name"][0])
            
            fig.add_trace(go.Scatter(
                x=dates,
                y=distances,
                mode="markers",
                marker=dict(size=8, opacity=0.7),
                text=names,
                hovertemplate="<b>%{text}</b><br><b>Date:</b> %{x|%Y-%m-%d}<br><b>Distance:</b> %{y:.2f} mi<extra></extra>",
                showlegend=False
            ))
            
            fig.update_layout(
                title="Distance Over Time",
                xaxis_title="Date",
                yaxis_title="Distance (miles)",
                hovermode="closest",
                height=500,
                template="plotly_white"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            if distance_df.height > 0:
                st.subheader("📊 All Activities - Distance vs Time")
                
                fig = go.Figure()
                
                # Generate run names with dates
                run_names = generate_run_names(activities_df)
                
                # Group by activity and plot
                for activity_id in distance_df["activity_id"].unique().to_list():
                    activity_data = distance_df.filter(pl.col("activity_id") == activity_id).sort("distance_mi")
                    run_name = run_names.get(activity_id, f"Run {activity_id}")
                    
                    # Convert seconds to HH:MM:SS for hover
                    time_labels = [format_time(int(s)) for s in activity_data["elapsed_seconds"].to_list()]
                    
                    fig.add_trace(go.Scatter(
                        x=activity_data["distance_mi"].to_list(),
                        y=activity_data["elapsed_seconds"].to_list(),
                        mode="lines",
                        name=run_name,
                        opacity=0.7,
                        hovertemplate="<b>%{fullData.name}</b><br><b>Distance:</b> %{x:.2f} mi<br><b>Time:</b> " + 
                                      "<span>" + "</span>".join([f"%{{y}} ({t})" for t in time_labels]) + "<extra></extra>",
                        customdata=time_labels,
                    ))
                
                fig.update_layout(
                    title="Distance vs Time - All Runs",
                    xaxis_title="Distance (miles)",
                    yaxis_title="Time (seconds)",
                    hovermode="x unified",
                    height=600,
                    template="plotly_white"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            
            # Personal best analysis
            st.subheader("🏃 Personal Best Analysis")
            
            pb_df = client.compute_personal_best_times(activities)
            
            if pb_df.height > 0:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Fastest Time to Each Distance**")
                    
                    fig = go.Figure()
                    
                    # Main curve
                    fig.add_trace(go.Scatter(
                        x=pb_df["distance_mi"].to_list(),
                        y=pb_df["pb_seconds"].to_list(),
                        mode="lines",
                        name="PB Time",
                        line=dict(color="rgb(0, 100, 200)", width=2),
                        customdata=pb_df["pb_time_hhmmss"].to_list(),
                        hovertemplate="<b>Distance:</b> %{x:.2f} mi<br><b>Time:</b> %{customdata}<extra></extra>"
                    ))
                    
                    fig.update_layout(
                        title="Fastest Time to Distance",
                        xaxis_title="Distance (miles)",
                        yaxis_title="Time (seconds)",
                        height=500,
                        template="plotly_white",
                        hovermode="x unified"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    st.write("**Fastest Pace at Each Distance**")
                    
                    fig = go.Figure()
                    
                    # Main curve
                    fig.add_trace(go.Scatter(
                        x=pb_df["distance_mi"].to_list(),
                        y=pb_df["pb_pace_min_mi"].to_list(),
                        mode="lines",
                        name="PB Pace",
                        line=dict(color="rgb(200, 100, 0)", width=2),
                        customdata=pb_df["pb_pace_mm_ss"].to_list(),
                        hovertemplate="<b>Distance:</b> %{x:.2f} mi<br><b>Pace:</b> %{customdata} min/mi<extra></extra>"
                    ))
                    
                    fig.update_layout(
                        title="Fastest Pace to Distance",
                        xaxis_title="Distance (miles)",
                        yaxis_title="Pace (min/mi)",
                        height=500,
                        template="plotly_white",
                        hovermode="x unified"
                    )
                    st.plotly_chart(fig, use_container_width=True)
    
    except requests.exceptions.HTTPError as e:
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg:
            st.error("❌ Authentication failed: Your Strava credentials are invalid or expired.")
            st.info("Please click 'Sign Out' and reconnect with Strava.")
        else:
            st.error(f"❌ Strava API error: {error_msg}")
    except Exception as e:
        st.error(f"❌ Error fetching data: {str(e)}")
        st.info("Please make sure your Strava credentials are correct and try again.")

else:
    st.info(
        """
        👈 **Click "Connect with Strava" in the sidebar to authenticate and view your metrics!**
        
        This dashboard displays:
        - 📊 Distance, duration, and pace statistics
        - 📈 Activity trends over time
        - 🏔️ Elevation gain tracking
        - 📋 Detailed activity list
        - 📍 Distance-time curves from TCX data
        """
    )
