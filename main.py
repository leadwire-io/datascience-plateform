from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from jinja2 import Environment, FileSystemLoader
import httpx, os, json, base64
from k8s import create_service, delete_service, list_user_services
from minio_client import ensure_bucket, get_storage_info

app = FastAPI()
jinja_env = Environment(loader=FileSystemLoader("/app/templates"))

KEYCLOAK_INTERNAL = os.getenv("KEYCLOAK_INTERNAL", "http://keycloak:8080/auth/realms/datalab")
KEYCLOAK_EXTERNAL = os.getenv("KEYCLOAK_EXTERNAL", "https://dtnum.nubo.local/auth/realms/datalab")
CLIENT_ID     = os.getenv("CLIENT_ID", "datalab-lite")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")
REDIRECT_URI  = os.getenv("REDIRECT_URI", "https://dtnum.nubo.local/callback")

SERVICES = {
    "jupyter": {"name": "JupyterLab",    "port": 8888, "icon": "🔬"},
    "rstudio": {"name": "RStudio",       "port": 8787, "icon": "📊"},
    "vscode":  {"name": "VSCode Server", "port": 8080, "icon": "💻"},
}

def render(template_name, **ctx):
    t = jinja_env.get_template(template_name)
    return HTMLResponse(t.render(**ctx))

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    username = request.cookies.get("username")
    if not username:
        return RedirectResponse("/login")
    services = list_user_services(username)
    return render("index.html", username=username,
                  services=services, catalog=SERVICES, active_types=set())

@app.get("/status", response_class=HTMLResponse)
async def status_page(request: Request):
    return render("status.html")

@app.get("/login")
async def login():
    url = (
        f"{KEYCLOAK_EXTERNAL}/protocol/openid-connect/auth"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=openid profile email"
    )
    return RedirectResponse(url)

@app.get("/callback")
async def callback(code: str, request: Request):
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.post(
            f"{KEYCLOAK_INTERNAL}/protocol/openid-connect/token",
            data={
                "grant_type": "authorization_code",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "code": code,
                "redirect_uri": REDIRECT_URI,
            }
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail=f"Auth failed: {resp.text}")

    tokens = resp.json()
    access_token = tokens["access_token"]
    payload = access_token.split(".")[1]
    payload += "=" * (4 - len(payload) % 4)
    user_info = json.loads(base64.b64decode(payload))
    username = user_info.get("preferred_username", "unknown")

    ensure_bucket(username)

    response = RedirectResponse("/", status_code=302)
    response.set_cookie("token", access_token, httponly=True)
    response.set_cookie("username", username, httponly=True)
    return response

@app.get("/logout")
async def logout():
    response = RedirectResponse(
        f"{KEYCLOAK_EXTERNAL}/protocol/openid-connect/logout"
        f"?client_id={CLIENT_ID}"
        f"&post_logout_redirect_uri=https://dtnum.nubo.local"
    )
    response.delete_cookie("token")
    response.delete_cookie("username")
    return response

@app.post("/api/launch/{service_type}")
async def launch(service_type: str, request: Request):
    username = request.cookies.get("username")
    if not username:
        raise HTTPException(status_code=401)
    if service_type not in SERVICES:
        raise HTTPException(status_code=400, detail="Service inconnu")
    svc = SERVICES[service_type]
    url, token, open_url = create_service(username, service_type, svc)
    return JSONResponse({"status": "ok", "url": url, "open_url": open_url, "token": token})

@app.delete("/api/delete/{service_name:path}")
async def delete(service_name: str, request: Request):
    username = request.cookies.get("username")
    if not username:
        raise HTTPException(status_code=401)
    delete_service(username, service_name)
    return JSONResponse({"status": "deleted"})

@app.get("/api/services")
async def services(request: Request):
    username = request.cookies.get("username")
    if not username:
        raise HTTPException(status_code=401)
    return JSONResponse(list_user_services(username))

@app.get("/api/storage")
async def storage(request: Request):
    username = request.cookies.get("username")
    if not username:
        raise HTTPException(status_code=401)
    return JSONResponse(get_storage_info(username))

@app.get("/health")
async def health():
    return JSONResponse({"status": "ok", "service": "DTNum Labs"})
