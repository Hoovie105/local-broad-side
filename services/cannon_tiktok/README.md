```
Run this command first
```
pip install -r requirements.txt

ALLWAYS WORK IN ROOT, NO NEED TO CD INTO FOLDER.

Start backend: fastapi dev, use uvicorn bare if u want to.
Must Tunnel for Development. Cuz tiktok a bitch.
lt --port 8002 --subdomain boardsideauth
uvicorn services.cannon_tiktok.main:app --port 8004 --reload

Currently tik tok MS is running via a tunnel and 17 other works arounds and even then
it only posts to drafts on da phone. once we have a real domain we can post directly.

access swagger docs: add /docs to end of url

adding routes(so kusta dont touch me):
Check main.py