"""Strava OAuth authentication module."""
import os
import requests
import streamlit as st
from typing import Dict, Any
from urllib.parse import urlencode


class StravaAuth:
    """Handle Strava OAuth authentication flow."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str = "http://localhost:8501",
    ):
        """Initialize Strava auth handler.
        
        Args:
            client_id: Strava OAuth client ID
            client_secret: Strava OAuth client secret
            redirect_uri: OAuth redirect URI (default for local Streamlit app)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.auth_url = "https://www.strava.com/oauth/authorize"
        self.token_url = "https://www.strava.com/api/v3/oauth/token"
        self.api_base_url = "https://www.strava.com/api/v3"

    def get_auth_url(self) -> str:
        """Generate Strava OAuth authorization URL.
        
        Returns:
            Authorization URL for user to click
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "read_all,activity:read_all",
            "state": "strava-oauth",
        }
        return f"{self.auth_url}?{urlencode(params)}"

    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token.
        
        Args:
            code: Authorization code from OAuth callback
            
        Returns:
            Token response containing access_token and refresh_token
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
        }
        response = requests.post(self.token_url, data=data)
        response.raise_for_status()
        return response.json()

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh expired access token.
        
        Args:
            refresh_token: Refresh token from previous auth
            
        Returns:
            New token response with updated access_token
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        response = requests.post(self.token_url, data=data)
        response.raise_for_status()
        return response.json()

    def get_athlete_info(self, access_token: str) -> Dict[str, Any]:
        """Get authenticated user's athlete information.
        
        Args:
            access_token: Valid Strava access token
            
        Returns:
            Athlete information dictionary
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(f"{self.api_base_url}/athlete", headers=headers)
        response.raise_for_status()
        return response.json()

    def get_athlete_activities(
        self, access_token: str, per_page: int = 30, page: int = 1
    ) -> list:
        """Get athlete's activities.
        
        Args:
            access_token: Valid Strava access token
            per_page: Number of activities per page (default 30, max 200)
            page: Page number for pagination
            
        Returns:
            List of activity dictionaries
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"per_page": per_page, "page": page}
        response = requests.get(
            f"{self.api_base_url}/athlete/activities",
            headers=headers,
            params=params,
        )
        response.raise_for_status()
        return response.json()

    def get_activity_details(self, access_token: str, activity_id: int) -> Dict[str, Any]:
        """Get detailed information about a specific activity.
        
        Args:
            access_token: Valid Strava access token
            activity_id: ID of the activity
            
        Returns:
            Activity details dictionary
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(
            f"{self.api_base_url}/activities/{activity_id}",
            headers=headers,
        )
        response.raise_for_status()
        return response.json()


def load_strava_auth() -> StravaAuth:
    """Load Strava auth with credentials from environment variables.
    
    Returns:
        StravaAuth instance
        
    Raises:
        ValueError: If STRAVA_CLIENT_ID or STRAVA_CLIENT_SECRET not set
    """
    client_id = os.getenv("STRAVA_CLIENT_ID")
    client_secret = os.getenv("STRAVA_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise ValueError(
            "STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET environment variables required"
        )

    redirect_uri = os.getenv("STRAVA_REDIRECT_URI", "http://localhost:8501")
    return StravaAuth(client_id, client_secret, redirect_uri)


def save_token_to_session(token_response: Dict[str, Any]) -> None:
    """Save token data to Streamlit session state.
    
    Args:
        token_response: Token response from OAuth endpoint
    """
    st.session_state.access_token = token_response["access_token"]
    st.session_state.refresh_token = token_response["refresh_token"]
    st.session_state.expires_at = token_response["expires_at"]
    st.session_state.is_authenticated = True


def is_authenticated() -> bool:
    """Check if user is authenticated.
    
    Returns:
        True if access token exists in session
    """
    return st.session_state.get("is_authenticated", False) and st.session_state.get(
        "access_token"
    )


def logout() -> None:
    """Clear authentication from session state."""
    st.session_state.access_token = None
    st.session_state.refresh_token = None
    st.session_state.expires_at = None
    st.session_state.is_authenticated = False
