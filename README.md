# EgressIPsApp (Prisma Access Egress IP Viewer)

A small Flask web application (Dockerized) that retrieves Prisma Access **Egress IP** data and presents it in a **filterable, refreshable** HTML table. Supports **Global** and **China** tenants via a dropdown selector. Secrets (API keys) are retrieved from **Azure Key Vault** using `DefaultAzureCredential`.

---

## Features

- Fetches Prisma Access Egress IPs from the Prisma API (per tenant)
- Presents data in a web table (Zone + Address Details)
- **Tenant dropdown**: `global` / `china`
- **Refresh button**: re-fetches latest data from the API (no restart required)
- Client-side **filtering** (quick search across visible rows)
- **Spinner** loading indicator while fetching/rendering
- Dockerized, runs as **non-root** user
- Persistent log file support (optional; see Logging notes)

---

## Project Structure

```text
EgressIPsApp/
├─ src/
│  ├─ egress_ips_api.py          # EgressIP client (API wrapper)
│  ├─ logs/                      # host-mounted logs (optional)
│  └─ webapp/
│     ├─ app.py                  # Flask app
│     ├─ templates/
│     │  └─ index.html           # UI
│     └─ static/
│        ├─ app.js               # UI logic (fetch/render/filter/spinner)
│        └─ app.css              # styling (scroll, sticky header, spinner)
├─ requirements.txt
├─ Dockerfile
├─ docker-compose.yml
└─ .env
```

---

## Prerequisites

- Docker + Docker Compose
- Access to the Prisma Egress IP API endpoints (Global + China)
- Azure Key Vault containing secrets for the Prisma API keys
- Host Linux environment using domain-backed groups (if applicable)


### .env File Configuration

Important: .env files are literal key=value. They do not evaluate shell expressions like $(id -u).

Example:
```text
# Build-time user mapping for bind-mounted volumes (literal integers)
UID=<UID of user to be used>
GID=<GID of user to be used>

# Azure Key Vault
KEYVAULT_URL=https://<your-kv-name>.vault.azure.net/

# Global (ROW) Prisma config
PRISMA_ROW_TENANT_TSG_ID=<TSG_ID>
PRISMA_ROW_EGRESS_IP_URL=https://api.prod6.datapath.prismaaccess.com/getPrismaAccessIP/v2
PRISMA_ROW_EGRESS_IP_API_KEY=<prisma-api-key-secret-name-in-keyvault>

# China Prisma config
PRISMA_CN_TENANT_TSG_ID=<TSG_ID>
PRISMA_CN_EGRESS_IP_URL=https://api.prod.datapath.prismaaccess.cn/getPrismaAccessIP/v2
PRISMA_CN_EGRESS_IP_API_KEY=<prisma-api-key-secret-name-in-keyvault>
```

### Dockerfile Notes (non-root + PYTHONPATH)

Key points implemented:

- PYTHONPATH=/app so imports like from src.egress_ips_api import EgressIP work reliably
- non-root appuser
- build args UID and GID so the container user matches the host bind-mounted folder ownership

### Docker-compose.yml Notes (ports + build args)
Make sure you include:

- ports: mapping so the webapp is reachable from your host browser
- build.args for UID/GID mapping
- bind mounts for development (./src:/app/src) and optional logs folder

Example (core parts):
```yaml
services:
  app:
    build:
      context: .
      args:
        UID: ${UID:-1000}
        GID: ${GID:-1000}
    ports:
      - "5000:5000"
    volumes:
      - ./src:/app/src
      - ./src/logs:/app/src/logs
```

### Notes on UID/GID in enterprise environments

- UID in bash is a readonly variable. Don’t try to export UID=....
- If you’re on a domain-joined system, your primary group can be a large numeric GID.
- Discover your domain group GID with:

```shell
getent group "domain users@omnia.aoglobal.com"
# Example output: ...:*:10400513:...
```
Use that numeric value as GID in .env.

---

## Running the App Using a Dedicated Local Host User

In some environments (especially enterprise or multi‑user systems), you may want the container to run as a **specific local host user account** rather than your interactive login user. This section documents how to:

- Create a dedicated local user on the host
- Grant that user permission to the log directory
- Retrieve the user’s numeric UID and GID
- Wire those values into Docker via `.env`
- Run the container safely as that user (without root)

---

### Why This Is Needed

Docker bind mounts respect **host filesystem ownership and permissions**.  
When writing logs to a host‑mounted directory, the container user must have:

- Matching **numeric UID**
- Matching **numeric GID**
- Write permissions on the directory **and any existing files**

Docker **cannot**:
- Create host users
- Change host file ownership
- Override enterprise filesystem or domain policies

Therefore, ownership must be correct **before** the container starts.

---

### Step 1: Create a Dedicated Local User on the Host

Run the following commands **on the host**, as an admin user:

```bash
sudo useradd \
  --system \
  --create-home \
  --shell /usr/sbin/nologin \
  egressips
```

Notes:

- --system creates a non‑login service user
- --nologin prevents interactive authentication
- The username egressips is an example

### Step 2: Create and Secure the Logs Directory
Create the logs directory and assign ownership to the new user:
```shell
sudo mkdir -p src/logs
sudo chown egressips:egressips src/logs
sudo chmod 775 src/logs
```

Verify:
```shell
ls -ld src/logs
```

Expected output pattern:
```text
drwxrwxr-x egressips egressips src/logs
```

### Step 3: Retrieve the User’s UID and GID
Docker permissions work on numeric IDs, not names.
Retrieve them:
```shell
id egressips
```

Example output:
```text
uid=1050(egressips) gid=1050(egressips)
```

Record these values.

### Step 4: Configure .env with UID and GID
Edit the project .env file and add literal numeric values:
```text
UID=1050
GID=1050
```

⚠️ Important:

- .env files do not evaluate shell expressions
- Do not use $(id -u) or similar
- Values must be plain integers

### Step 5: Ensure Docker Uses These Values
**docker-compose.yml**

The compose file must pass UID/GID at build time:
```yaml
services:
  app:
    build:
      context: .
      args:
        UID: ${UID}
        GID: ${GID}
    volumes:
      - ./src:/app/src
      - ./src/logs:/app/src/logs
```

**Dockerfile (excerpt)**
```dockerfile
ARG UID
ARG GID

RUN groupadd -g ${GID} appgroup \
 && useradd -m -u ${UID} -g ${GID} appuser

USER appuser
```
This ensures the container user has identical IDs to the host user.

### Step 6: Build and Run the Container
Always rebuild when UID/GID changes:
```shell
docker compose down
docker compose build --no-cache
docker compose up
```

---

## Flask App Overview

### Region configuration
The app loads Prisma config from Key Vault and returns a mapping:
```python
return {
  "global": {"url": ..., "key": ...},
  "china":  {"url": ..., "key": ...},
}
```

### API Endpoint

- GET /api/egress-ips?region=global|china
- Returns flattened rows for table rendering:

  - zone
  - service_type
  - address_type
  - address
  - node_names


Only zone + address_details are used from the Prisma API response.

### UI

- GET / serves the HTML page
- static/app.js fetches /api/egress-ips and renders rows into <tbody id="egressTable">

---

## Build & Run

1) Ensure the logs directory exists (if using file logging)
```shell
mkdir -p src/logs
chmod 775 src/logs
```

2) Build (no cache recommended when changing UID/GID)
```shell
docker compose down
docker compose build --no-cache
```
During build you should see the correct UID/GID being used, e.g.:
```shell
RUN groupadd -g 10400513 appgroup && useradd -m -u 1000 -g 10400513 appuser
```

3) Run
```shell
docker compose up
```

4) Access the app from host desktop
```text
http://127.0.0.1:5000
```

---

## Logging

### Docker-native logging (recommended)
Logs to stdout/stderr and view via:
```shell
docker compose logs -f app
```

### File logging (optional)
If you enable logging.FileHandler("src/logs/app.log"):

- Ensure src/logs exists and is writable
- On domain systems ensure container GID matches directory group GID
- If the log file already exists and is owned by the wrong UID/GID, you may get:
PermissionError: [Errno 13] Permission denied

Fix by deleting the old file so the container can recreate it:
```shell
rm -f src/logs/app.log
```