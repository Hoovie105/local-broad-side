```
Run this command first
```
pip install -r requirements.txt

ALWAYS WORK IN ROOT, NO NEED TO CD INTO FOLDER.

## Docker Setup

Build and run the Reels container from the root directory:

```bash
docker build -f Reels/Dockerfile -t broadside-reels .
docker run -p 8001:8000 `
  --env-file .env `
  broadside-reels
```

Reels will be available at `http://localhost:8001`

## Local Development

Start Reels service:
uvicorn services.cannon_insta.main:app --port 8002 --reload

access swagger docs: add /docs to end of url

adding routes(so kusta dont touch me):
Check main.py

Testing IG_TOKEN: IGAA4UwWcKsGtBZAFpMM190ZAHlxM0MyQ3M3MFJiak5ySHhlOXR6cExEVGNucDl0SXBiLXhlVklqWjZAZAM1ptWGU4QmZAabWVqSmh0TzVJN0NVMEtaWFB2c0FIeUYyRlY1RDkyVFNHWVpXWGppbUdjc3huRkRScjVMazYtOWQ2a1JRUQZDZD

command:
curl.exe -X POST http://localhost:8000/api/v1/publish `
  -F "video=@D:\BroadSide\testvid.mp4;type=video/mp4" `
  -F "caption=Test upload" `
  -F "platforms=instagram" `
  -F "ig_access_token=EAIHcA71JPa4BRVWzK9rCh6DbXX7sq0Dm750TKuiJbeBocN5rXk9g0tv7o00B1VTTORrkmDw0kNihgxwXDNXFNW0xqy1lcpslmwu3dNq026wZBP2rSYsD6ZCM4ntM7ZAS07HWTg3WzlJFBnAnJNxBa9xnOZCzYMR2oMwcjPRqLBWVE0a6aY2TfZAPin9DQGnSDaCX4QSxoCtPuk6PdYzDZBgUjzXVZABvc22owwmAPuAFYNkNHIodVAMZC0K6LSJZB6SyZBZBcdyZA9PBULs8sl3nKWhcJCB3" `
  -F "ig_user_id=17841421509503556"

  curl.exe http://localhost:8000/api/v1/jobs/

