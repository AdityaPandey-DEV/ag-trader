# AG_TRADER Cloud Deployment Guide

Follow these steps to deploy your trading system 24/7 for free.

### 🌐 Cloud & Network Configuration
When deploying to Render/Vercel, you need to tell the Engine where the API is:

1.  **BACKEND_URL**: In your backend environment (Render), set this to your API's public URL (e.g., `https://my-api.onrender.com`). The Engine uses this to push updates if running in distributed mode.
2.  **NEXT_PUBLIC_API_URL**: In your frontend environment (Vercel), set this to your API's host (e.g., `my-api.onrender.com`). Do not include `http://` or `https://` if using the websocket auto-protocol logic.

## 1. Backend & Engine (Render.com)

Since we've refactored the code, Render will now run both the **API** and the **Trading Engine** in a single process.

1.  **Push your code to GitHub**.
2.  Go to [Render.com](https://render.com) and create a **Web Service**.
3.  Connect your repository.
4.  **Settings**:
    *   **Build Command**: `pip install -r requirements.txt`
    *   **Start Command**: `gunicorn -w 1 -k uvicorn.workers.UvicornWorker dashboard.api:app --bind 0.0.0.0:$PORT`
    *   *Note: We use `-w 1` because the engine runs as a background thread inside the API process.*
5.  **Environment Variables**:
    *   `GEMINI_API_KEY`: Your Google Gemini API Key.
    *   `PYTHONPATH`: `.`

---

## 2. Frontend Dashboard (Vercel)

1.  Connect your repo to [Vercel](https://vercel.com).
2.  Set the **Root Directory** to `frontend`.
3.  **Environment Variables**:
    *   `NEXT_PUBLIC_API_URL`: Your Render URL (e.g., `ag-trader-backend.onrender.com`). *Do not include http/https.*
4.  Deploy!

---

## 3. Keep it Alive (The Sleep Fix)

Render's free tier sleeps after 15 mins. To keep your engine trading 24/7:
1.  Go to [Cron-job.org](https://cron-job.org) or [UptimeRobot](https://uptimerobot.com).
2.  Create a "Monitor" that pings your Render URL (e.g., `https://your-app.onrender.com/status`) every 5-10 minutes.
3.  This keeps the backend awake and the engine running! 🤖📈

---

## 4. Local Testing Tip
To test locally after these changes, you only need to run the API now:
```bash
python3 dashboard/api.py
```
*The engine will start automatically!*
