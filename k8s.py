import docker, random, string, secrets, os, socket

DOMAIN         = os.getenv("DOMAIN", "localhost")
NGINX_CONF_DIR = "/etc/nginx/services"
NETWORK        = os.getenv("DOCKER_NETWORK", "dtnum-network")

PORTS  = {"jupyter": 8888, "rstudio": 8787, "vscode": 8080}
IMAGES = {
    "jupyter": "jupyter/scipy-notebook:latest",
    "rstudio": "rocker/rstudio:latest",
    "vscode":  "codercom/code-server:latest",
}

def get_docker_client():
    return docker.from_env()

def random_id(length=5):
    return ''.join(random.choices(string.digits, k=length))

def generate_token(length=12):
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))

def free_port():
    with socket.socket() as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def get_env(service_type, token):
    return {
        "jupyter": {"JUPYTER_ENABLE_LAB": "yes", "JUPYTER_TOKEN": token},
        "rstudio": {"PASSWORD": token, "USER": "rstudio"},
        "vscode":  {"PASSWORD": token},
    }.get(service_type, {})

def write_nginx_location(name, port):
    os.makedirs(NGINX_CONF_DIR, exist_ok=True)
    with open(f"{NGINX_CONF_DIR}/{name}.conf", "w") as f:
        f.write(f"""
location /{name}/ {{
    proxy_pass         http://{name}:{port}/{name}/;
    proxy_set_header   Host $host;
    proxy_set_header   X-Real-IP $remote_addr;
    proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header   X-Forwarded-Proto https;
    proxy_http_version 1.1;
    proxy_set_header   Upgrade $http_upgrade;
    proxy_set_header   Connection "upgrade";
    proxy_read_timeout 300s;
}}
""")

def remove_nginx_location(name):
    try:
        os.remove(f"{NGINX_CONF_DIR}/{name}.conf")
    except:
        pass

def reload_nginx():
    try:
        get_docker_client().containers.get("dtnum-nginx").exec_run("nginx -s reload")
    except Exception as e:
        print(f"Nginx reload error: {e}")

def create_service(username, service_type, svc_config):
    client = get_docker_client()
    uid    = random_id()
    name   = f"{username}-{service_type}-{uid}"
    port   = PORTS.get(service_type, 8080)
    token  = generate_token()

    use_nginx = (service_type == "jupyter")

    run_kwargs = dict(
        image=IMAGES.get(service_type),
        name=name,
        detach=True,
        environment=get_env(service_type, token),
        labels={
            "dtnum-labs": "true",
            "user": username,
            "service-type": service_type,
            "instance-id": uid,
            "token": token,
        },
        restart_policy={"Name": "unless-stopped"},
    )

    if use_nginx:
        run_kwargs["network"] = NETWORK
        run_kwargs["command"] = [
            "start-notebook.py",
            f"--ServerApp.base_url=/{name}/",
            f"--ServerApp.token={token}",
            "--ServerApp.allow_origin=*",
            "--ServerApp.trust_xheaders=True",
        ]
        write_nginx_location(name, port)
        reload_nginx()
        open_url = f"https://{DOMAIN}/{name}/lab?token={token}"
        url = f"https://{DOMAIN}/{name}/"
    else:
        host_port = free_port()
        run_kwargs["ports"] = {f"{port}/tcp": host_port}
        run_kwargs["network"] = NETWORK
        run_kwargs["labels"]["host_port"] = str(host_port)
        url = f"http://{DOMAIN}:{host_port}/"
        open_url = url

    client.containers.run(**run_kwargs)
    return url, token, open_url

def delete_service(username, service_name):
    try:
        c = get_docker_client().containers.get(service_name)
        stype = c.labels.get("service-type", "")
        c.stop(timeout=5)
        c.remove()
        if stype == "jupyter":
            remove_nginx_location(service_name)
            reload_nginx()
    except:
        pass

def list_user_services(username):
    result = []
    try:
        for c in get_docker_client().containers.list(all=True, filters={"label": f"user={username}"}):
            stype     = c.labels.get("service-type", "")
            token     = c.labels.get("token", "")
            host_port = c.labels.get("host_port", "")
            ready     = c.status == "running"

            if stype == "jupyter":
                url = f"https://{DOMAIN}/{c.name}/"
            else:
                url = f"http://{DOMAIN}:{host_port}/" if host_port else "#"

            result.append({
                "name":   c.name,
                "type":   stype,
                "ready":  ready,
                "url":    url,
                "token":  token,
                "status": c.status,
            })
    except Exception as e:
        print(f"List error: {e}")
    return result
