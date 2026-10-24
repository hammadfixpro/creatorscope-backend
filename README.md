# CreatorScope Backend (Render deploy)

FastAPI backend for CreatorScope AI frontend at https://creatorscope-ai.pages.dev

Deploy: Render > New > Web Service > Public Git Repository (paste this repo URL)
Render reads render.yaml automatically.
Free plan notes: service sleeps after ~15 min idle (first request ~1 min), disk is ephemeral so SQLite data resets on restart/redeploy.
Without YOUTUBE_API_KEY / GEMINI_API_KEY env vars it runs in labelled demo mode; add keys in Render > Environment later.
