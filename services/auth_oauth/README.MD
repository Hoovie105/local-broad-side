```
Run this command first
```
pip install -r requirements.txt

ALLWAYS WORK IN ROOT, NO NEED TO CD INTO FOLDER.

Start backend: fastapi dev, use uvicorn bare if u want to.
uvicorn services.auth_oauth.main:app --port 8001 --reload

access swagger docs: add /docs to end of url

adding routes(so kusta dont touch me):
Check main.py for pages
Check v1 under api folder for Keel routes