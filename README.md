# 🏃 Strava Metrics Dashboard

A Streamlit dashboard that connects to the Strava API using OAuth 2.0 to display your running and cycling metrics.

## ✨ Features

- 🔐 **OAuth 2.0 Authentication** - Secure connection to your Strava account
- 📊 **Real-time Metrics** - Distance, duration, pace, and elevation tracking
- 📈 **Interactive Charts** - Visualize your activity trends over time
- 🏔️ **Activity Breakdown** - Filter by activity type and date range
- 📋 **Activity List** - Detailed view of all your activities

## 🚀 Quick Start

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd strava-metrics
   ```

2. **Create a Strava OAuth Application**
   - Go to https://www.strava.com/settings/api
   - Create a new OAuth application
   - Note your **Client ID** and **Client Secret**

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your credentials:
   ```
   STRAVA_CLIENT_ID=your_client_id
   STRAVA_CLIENT_SECRET=your_client_secret
   STRAVA_REDIRECT_URI=http://localhost:8501
   ```

4. **Run the dashboard**
   ```bash
   uv run streamlit run app.py
   ```

   Or use the configured script:
   ```bash
   uv run dashboard
   ```

5. **Authenticate**
   - Click the "Connect with Strava" link in the sidebar
   - Authorize the application
   - You'll be redirected back to the dashboard with your metrics loaded

## 📁 Project Structure

```
strava-metrics/
├── app.py                 # Main Streamlit application
├── strava_auth.py         # OAuth authentication module
├── strava_api.py          # Strava API client
├── .env.example           # Environment variables template
├── pyproject.toml         # Project dependencies
└── README.md              # This file
```

## 🔐 How OAuth Works

The dashboard uses Strava's OAuth 2.0 flow:

1. User clicks "Connect with Strava" button
2. Redirected to Strava's authorization page
3. User grants permission to read activities
4. Strava redirects back with an authorization code
5. Dashboard exchanges code for access token
6. Token is saved to session state for API calls
7. User can now view their metrics

## 📊 API Endpoints Used

- `/api/v3/athlete` - Get authenticated athlete's profile
- `/api/v3/athlete/activities` - Get list of activities
- `/api/v3/activities/{id}` - Get detailed activity info

## 🛠️ Development

### Install dependencies manually
```bash
uv pip install streamlit requests python-dotenv pandas
```

### Run in development mode
```bash
uv run streamlit run app.py --logger.level=debug
```

## 🔒 Security Notes

- **Do not commit `.env`** - Add to `.gitignore`
- Keep your **Client Secret** safe
- The access token is stored only in Streamlit's session state
- Tokens expire after 6 hours (refresh tokens are available for 30 days)

## 📝 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `STRAVA_CLIENT_ID` | Yes | OAuth Client ID from Strava |
| `STRAVA_CLIENT_SECRET` | Yes | OAuth Client Secret from Strava |
| `STRAVA_REDIRECT_URI` | No | OAuth redirect URI (default: `http://localhost:8501`) |

## 🐛 Troubleshooting

### "Configuration error: STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET not set"
- Make sure your `.env` file exists and is in the project root
- Check that variable names are spelled correctly
- Restart the Streamlit app after editing `.env`

### "Authentication failed"
- Verify your Client ID and Secret are correct
- Check that your Strava API application has the correct redirect URI
- Try logging out and reconnecting

### Activities not loading
- Make sure you've authorized the application
- Check that your Strava account has some activities
- Try refreshing the page

## 📚 Resources

- [Strava API Documentation](https://developers.strava.com/)
- [Strava OAuth Documentation](https://developers.strava.com/docs/authentication/)
- [Streamlit Documentation](https://docs.streamlit.io/)

## 📄 License

See LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Feel free to open issues and pull requests.