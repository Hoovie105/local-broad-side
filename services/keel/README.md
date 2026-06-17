```
Run this command first
```
pip install -r requirements.txt

ALLWAYS WORK IN ROOT, NO NEED TO CD INTO FOLDER.

## Docker Setup

Build and run the Backend container from the root directory:

```bash
docker build -f Backend/Dockerfile -t broadside-backend .
docker run -p 8000:8000 `
  --env-file .env `
  -v "$PWD/Backend/media:/app/media" `
  broadside-backend
```

The Docker image includes ffmpeg for video metadata extraction.

## Local Development

Start backend: fastapi dev, use uvicorn bare if u want to.
sudo docker compose down -v
sudo docker compose up -d
uvicorn services.keel.main:app --port 8000 --reload
ngrok http 8000 "in ngrok terminal for dev"
python -m http.server 3000 "for passing frontend as HTTP server"

access swagger docs: add /docs to end of url

adding routes(so kusta dont touch me):
Check main.py for pages
Check v1 under api folder for Keel routes

WINDOWS REQUIRMENTS:
need to install winget to install ffmpeg(makes things realy easy"I assume" for later):

Run in admin shell:
Add-AppxPackage -RegisterByFamilyName -MainPackage Microsoft.DesktopAppInstaller_8wekyb3d8bbwe -ForceApplicationShutdown

winget --version

Run in shell:
winget install ffmpeg
*RESTART SHELL*
ffprobe -version
