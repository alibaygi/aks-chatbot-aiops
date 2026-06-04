# How It Works — A Beginner's Story

This document walks through what actually happens inside your **AKS cluster** when
a user opens the chatbot, logs in, and sends a message.

---

## The Cast of Characters

Before the story starts, meet the players:

| Name | What it is | Think of it as |
|---|---|---|
| **AKS** | Azure Kubernetes Service — a managed Kubernetes cluster running on Azure VMs | A data centre Azure runs for you |
| **Pod** | A running container (your app code) | A process living inside that data centre |
| **Service** | A stable network address that routes traffic to a pod | A receptionist with a fixed desk number |
| **ConfigMap** | A place to store non-secret configuration | A sticky note pinned to the pod |
| **Secret** | A place to store sensitive credentials | A locked safe next to the pod |
| **PVC** | A persistent volume claim — reserved disk space | A hard drive attached to the postgres pod |

You have three pods running:

```
[ frontend pod :3000 ] ←──── browser
[ backend pod  :8000 ] ←──── frontend pod (internally)
[ postgres pod :5432 ] ←──── backend pod (internally)
```

And three Services acting as their receptionists:

```
frontend-service  → port 3001  (LoadBalancer — reachable from the internet)
backend-service   → port 8001  (ClusterIP    — internal only)
postgres-service  → port 5432  (ClusterIP    — internal only)
```

---

## Part 0 — Before Any User Arrives (Startup)

When you run `helm upgrade --install chatbot k8s/aks/chart ...`, Helm renders the chart
templates into Kubernetes manifests and applies them. Kubernetes then:

1. Creates the **ConfigMaps and Secrets** first — these are just data stored in the
   cluster, no containers yet.

2. Creates the **PVC** — reserves disk for postgres data. On AKS this is backed by a
   real **Azure Disk**, provisioned automatically via the built-in `managed-csi`
   StorageClass. The data lives on that disk, not on any single node.

3. Starts the **postgres pod**. The official `postgres:16-alpine` image reads
   `POSTGRES_USER`, `POSTGRES_DB`, and `POSTGRES_PASSWORD` from the ConfigMap/Secret
   (injected as environment variables) and initialises the database on the reserved
   disk. Data written here survives pod restarts because it lives on the PVC, not
   inside the container.

4. Starts the **backend pod**. AKS pulls the image from your private **ACR** using its
   managed identity. On startup, FastAPI:
   - Creates the app tables (`users`, `conversations`, `documents`) in postgres if they
     don't exist.
   - Connects to postgres a second time via LangGraph to set up the memory/checkpoint
     tables used by the AI agent.
   - Begins listening for HTTP requests on port 8000.

5. Starts the **frontend pod** (image also pulled from ACR). Next.js starts its Node.js
   server on port 3000. It reads `BACKEND_URL=http://backend-service:8001` from the
   ConfigMap so it knows where to forward API calls.

6. Azure provisions a **public IP** for `frontend-service`. Because it is a
   `LoadBalancer` Service, AKS asks Azure for an Azure Load Balancer and a public IP
   (this takes ~60 seconds). Once assigned, anyone on the internet can reach the app at
   `http://<EXTERNAL-IP>:3001`. You find that IP with
   `kubectl get service frontend-service`.

---

## Part 1 — The User Opens the Browser

```
Browser → http://<EXTERNAL-IP>:3001
```

1. The browser sends an HTTP request to port 3001 on the frontend's public IP.

2. The **Azure Load Balancer** in front of `frontend-service` receives the request and
   routes it into the cluster.

3. `frontend-service` is a LoadBalancer Service. It forwards the request to the
   **frontend pod** on port 3000 (its `targetPort`).

4. The Next.js server inside the frontend pod serves the React page HTML, CSS, and
   JavaScript back to the browser.

5. The browser renders the login page. No backend has been touched yet — this is just
   a static page being delivered.

---

## Part 2 — The User Logs In

The user types their email and password and clicks **Login**.

```
Browser → POST /api/v1/auth/login
```

### Step 2a — Browser to Frontend Pod

The browser sends a `POST` request to `/api/v1/auth/login` — a **relative URL**,
meaning it goes to the same host the page was loaded from: `<EXTERNAL-IP>:3001`.

Azure Load Balancer → `frontend-service` → **frontend pod :3000**

### Step 2b — Frontend Pod Proxies to Backend

Here is a key architectural detail: **the browser never talks to the backend directly.**
The Next.js server acts as a middleman (a "reverse proxy").

`next.config.ts` contains a rewrite rule:

> "Any request starting with `/api/v1/` — forward it to `$BACKEND_URL`."

`$BACKEND_URL` is `http://backend-service:8001` (from the ConfigMap). This is an
address that only exists *inside* the cluster — your browser could never reach it
directly. But the Next.js server *is* inside the cluster, so it can.

Next.js forwards the request:

```
Frontend pod → http://backend-service:8001/api/v1/auth/login
```

`backend-service` is a ClusterIP Service. It receives the request and routes it to
the **backend pod :8000**.

### Step 2c — Backend Checks Credentials

The FastAPI backend receives the login request. It:

1. Queries **postgres** (`SELECT * FROM users WHERE email = ?`) to find the user.
   This travels: `backend pod → postgres-service :5432 → postgres pod :5432`.

2. Verifies the hashed password stored in the database matches what the user typed.

3. If correct, it creates a **JWT token** — a small, cryptographically signed string
   that proves "this user is who they say they are." It is signed using `SECRET_KEY`
   (from the backend Secret) with the `HS256` algorithm (from the backend ConfigMap).
   The token expires after 7 days (`ACCESS_TOKEN_EXPIRE_MINUTES = 10080`).

4. Returns the token in the HTTP response.

### Step 2d — Response Travels Back

```
Backend pod → backend-service → frontend pod → frontend-service → Azure Load Balancer → Browser
```

The browser receives the JWT token and stores it in `localStorage`. From this point
on, **every request the browser makes includes this token** in the `Authorization`
header, so the backend knows who is asking.

---

## Part 3 — The User Sends a Chat Message

The user types "What is the capital of France?" and hits Send.

```
Browser → POST /api/v1/chat/{conversation_id}/messages
         Authorization: Bearer <jwt_token>
         Body: { "content": "What is the capital of France?" }
```

The request follows the same path as login:

```
Browser → Azure Load Balancer → frontend-service → frontend pod (Next.js proxy)
       → backend-service → backend pod (FastAPI)
```

### What the Backend Does with the Message

1. **Verifies the JWT token.** Uses `SECRET_KEY` to check the token's signature. If
   it's invalid or expired, it returns 401 Unauthorized immediately.

2. **Saves the user's message** to the `conversations` table in postgres.

3. **Runs the AI agent** (LangGraph). The agent:
   - Loads the conversation's **short-term memory** (recent messages) from postgres
     via the LangGraph checkpointer tables.
   - Loads the user's **long-term memory** (saved preferences and facts about the
     user) from postgres via the LangGraph store tables.
   - Decides if it needs to search the web (Tavily API — this goes out to the
     internet), search the user's uploaded documents, look up user info, or save new
     user info.
   - Calls the **OpenAI API** (also out to the internet) to generate the reply.

4. **Saves the AI reply** to postgres.

5. **Returns the reply** in the HTTP response.

### Response Travels Back

```
Backend pod → backend-service → frontend pod → frontend-service → Azure Load Balancer → Browser
```

The browser receives the reply and the React UI renders it as a new message bubble.

---

## The Full Picture

```
INTERNET
┌─────────────────────────────────────────────────────────────────┐
│  Browser                                                        │
│    │  http://<EXTERNAL-IP>:3001                                  │
│    ▼                                                            │
│  Azure Load Balancer (public IP)                                │
│    │                                                            │
│  ════════════════════ AKS CLUSTER ════════════════════════════  │
│  │                                                              │
│  │  frontend-service (LoadBalancer :3001)                       │
│  │    │                                                         │
│  │    ▼                                                         │
│  │  frontend pod (Next.js :3000)                                │
│  │    │  proxies /api/v1/* via BACKEND_URL                      │
│  │    ▼                                                         │
│  │  backend-service (ClusterIP :8001)                           │
│  │    │                                                         │
│  │    ▼                                                         │
│  │  backend pod (FastAPI :8000)                                 │
│  │    │  reads/writes users, conversations, agent memory        │
│  │    ▼                                                         │
│  │  postgres-service (ClusterIP :5432)                          │
│  │    │                                                         │
│  │    ▼                                                         │
│  │  postgres pod ──► PVC (Azure Disk via managed-csi)           │
│  │                                                              │
│  ════════════════════════════════════════════════════════════   │
│                                                                 │
│                          │ OpenAI API  │ Tavily API             │
│                          └─────────────────── internet ──►      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Why Services Exist (and Why You Can't Use Pod IPs)

You might wonder: why not just give the frontend the backend pod's IP address directly?

Because **pod IPs are temporary**. Every time a pod restarts (crash, redeploy, update),
it gets a new IP. If the frontend had the old IP hardcoded, it would break.

A **Service** has a fixed, stable address that Kubernetes keeps alive regardless of
what happens to the pods behind it. The frontend always talks to `backend-service`,
and Kubernetes silently routes that to whatever pod is currently running. This is the
core idea behind Kubernetes networking.

---

## Deploy Order and Commands

On AKS you deploy the whole stack with a single Helm command — Helm applies the
manifests in the right order, and Kubernetes brings up postgres, backend, and frontend.

```bash
# 1. Deploy (or upgrade) the whole release
helm upgrade --install chatbot k8s/aks/chart \
  -f k8s/aks/chart/values-secrets.yaml \
  --set backend.image.tag=$TAG \
  --set frontend.image.tag=$TAG

# 2. Watch pods come up
kubectl get pods -w

# 3. Get the public IP Azure assigned to the frontend (~60s to appear)
kubectl get service frontend-service -w

# 4. Open the app
open http://<EXTERNAL-IP>:3001

# 5. Useful debugging commands
kubectl logs -f deployment/backend-deployment    # backend logs
kubectl logs -f deployment/frontend-deployment   # frontend logs
kubectl logs -f statefulset/postgres             # postgres logs
kubectl describe pod <pod-name>                  # details + events if a pod won't start
```
