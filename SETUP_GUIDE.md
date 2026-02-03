# 🚀 Setup Guide - Strava Metrics Dashboard with OAuth

## Step-by-Step Instructions

### 1. Create Strava OAuth Application

1. Go to https://www.strava.com/settings/api
2. Click "Create an API Application"
3. Fill in the application details:
   - **Application Name**: Strava Metrics Dashboard (or your choice)
   - **Category**: Data Analysis
   - **Website**: http://localhost:8501 (for local testing)
   - **Authorization Callback Domain**: localhost
4. Accept the terms and create the application
5. Copy your **Client ID** and **Client Secret**

### 2. Configure Environment Variables

```bash
# Create .env file from template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Add your credentials:
```
STRAVA_CLIENT_ID=your_actual_client_id_here
STRAVA_CLIENT_SECRET=your_actual_client_secret_here
STRAVA_REDIRECT_URI=http://localhost:8501
```

### 3. Install Dependencies (if not using uv)

```bash
pip install -r requirements.txt
```

### 4. Run the Dashboard

Using `uv`:
```bash
uv run streamlit run app.py
```

Or directly with Python:
```bash
streamlit run app.py
```

### 5. Authenticate

1. Open your browser to http://localhost:8501
2. Click the "🔗 Click here to connect with Strava" link in the sidebar
3. Authorize the application on Strava's website
4. You'll be redirected back with your metrics loaded!

## 🔑 Important Notes

### For Local Development

- The default redirect URI is `http://localhost:8501`
- Make sure this matches your Strava OAuth application settings
- If running on a different port, update `.env`:
  ```
  STRAVA_REDIRECT_URI=http://localhost:8502
  ```

### For Production/Cloud Deployment

If deploying to Streamlit Cloud or another platform:

1. Update `STRAVA_REDIRECT_URI` in `.env` to your app's URL:
   ```
   STRAVA_REDIRECT_URI=https://your-app-name.streamlit.app
   ```

2. Add the callback domain to your Strava OAuth app settings

3. Set environment variables in your deployment platform

## 📚 File Descriptions

- **app.py** - Main Streamlit application with UI and data visualization
- **strava_auth.py** - OAuth 2.0 authentication handling
- **strava_api.py** - Strava API client for fetching activities
- **.env.example** - Template for environment variables (copy to .env)
- **pyproject.toml** - Project dependencies and configuration

## 🆘 Troubleshooting

### Issue: "STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET not set"

**Solution:**
- Verify `.env` file exists in the project root
- Check variable names are spelled correctly
- Make sure there are no extra spaces around the `=` sign
- Restart the Streamlit app after editing `.env`

### Issue: OAuth callback fails

**Solution:**
- Verify your Client ID and Secret are correct
- Check that your Strava OAuth app's redirect URI matches exactly
- If using HTTPS, make sure both use HTTPS (or both HTTP)
- Clear browser cookies and try again

### Issue: No activities appear

**Solution:**
- Make sure you have activities logged in your Strava account
- Verify you've authorized the application
- Check your Strava privacy settings allow the app to read activities
- Try logging out and reconnecting

## 🔐 Security Best Practices

1. **Never commit your `.env` file** - It's in `.gitignore` for a reason!
2. **Keep your Client Secret safe** - Don't share it or expose it in logs
3. **Use HTTPS in production** - Especially for the redirect URI
4. **Rotate credentials regularly** - If you suspect a leak

## 📖 Additional Resources

- [Strava API Documentation](https://developers.strava.com/)
- [Strava OAuth Flow](https://developers.strava.com/docs/authentication/)
- [Streamlit Documentation](https://docs.streamlit.io/)

Happy tracking! 🏃‍♂️
