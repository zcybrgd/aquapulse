### Required API Credentials

Before beginning configuration, ensure you have obtained the following API keys from their respective provider consoles:

* **Groq API Key**: Required for the LLM Policy Engine and Narration agents (`ChatGroq`).
* **Nokia Network-as-Code (RapidAPI) Key**: Required for CAMARA Device Reachability and Congestion insights.



---

---

1. **Create Environment (.env) Files:** Configuration.
Create three separate `.env` files in their respective project directories as specified below.

**1. Root Environment File (`./.env`)**

```ini
RAPIDAPI_HOST="network-as-code.nokia.rapidapi.com"
RAPIDAPI_KEY="YOUR_NOKIA_RAPIDAPI_KEY"
GROQ_API_KEY="YOUR_GROQ_API_KEY"
RESPONSE_AGENT_MODEL="openai/gpt-oss-20b"
GROQ_MODEL="openai/gpt-oss-20b"
WEBHOOK_URL="https://YOUR-NGROK-URL.ngrok-free.app"
CONGESTION_NOTIFICATION_URL="https://example.com/notifications"
CONGESTION_NOTIFICATION_AUTH_TOKEN="your_congestion_notification_auth_token"
REDIS_HOST="localhost"
REDIS_PORT=6380

```

**2. Platform Backend Environment (`plateform/backend/.env`)**

```ini
POSTGRES_DB=aquapulse
POSTGRES_USER=aquapulse
POSTGRES_PASSWORD=aquapulse
POSTGRES_PORT=5432
DATABASE_URL=postgresql+psycopg://aquapulse:aquapulse@127.0.0.1:5432/aquapulse
TEST_DATABASE_URL=postgresql+psycopg://aquapulse:aquapulse@127.0.0.1:5432/aquapulse_test
TELEMETRY_SIMULATOR_ENABLED=false
NOKIA_NETWORK_API_ENABLED=false
NOKIA_NETWORK_API_MODE=mock

```

**3. Anomaly Investigation Agent Environment (`agents/investigation_agent/.env`)**

```ini
RAPIDAPI_KEY="YOUR_NOKIA_RAPIDAPI_KEY"
RAPIDAPI_HOST="network-as-code.nokia.rapidapi.com"
GROQ_API_KEY="YOUR_GROQ_API_KEY"
REDIS_URL="redis://127.0.0.1:6380/0"

```

*Verification:* Verify that all three files exist in their target directories by running `ls .env plateform/backend/.env agents/investigation_agent/.env` in your terminal.


2. **Start Ngrok and Expose Webhook API:** Port 9001.
Start an ngrok tunnel pointing to port `9001` (the Network Agent Webhook API port):

```bash
ngrok http 9001

```

1. Copy the generated `https://` forwarding URL from the ngrok terminal output (e.g., `[https://a1b2-34-56-78-90.ngrok-free.app](https://a1b2-34-56-78-90.ngrok-free.app)`).
2. Open `./.env` in your editor and update the `WEBHOOK_URL` value with this exact URL:



```ini
WEBHOOK_URL="https://a1b2-34-56-78-90.ngrok-free.app"

```

*Verification:* Ping the ngrok URL in your browser or run `curl -I https://<YOUR-NGROK-URL>.ngrok-free.app` to verify the tunnel resolves.


3. **Initialize Database & Migration Seeds:** First-time setup.
Start the PostgreSQL/TimescaleDB container and apply Alembic migrations:

```bash
# 1. Start database container
cd plateform
docker compose up -d aquapulse-db
cd ..

# 2. Run backend migrations and seed data
cd plateform/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m app.scripts.seed_database
cd ../..

```

*Verification:* Run `docker ps` and confirm the `aquapulse-db` container shows status `Up (healthy)`.


4. **Launch AquaPulse Core Stack:** Master Script.
Grant execution permissions to `run.sh` and execute the master launcher from the repository root:

```bash
chmod +x run.sh
./run.sh

```

This automatically verifies required tools, sets up Python virtual environments, installs dependencies (including Node.js/npm packages), starts Docker infrastructure, and launches all microservices and background agents.

*Verification:* Observe terminal logs for `[ OK ]` checkmarks across all services and confirm the startup banner lists active endpoints.


---

### Accessing System Services

Once `run.sh` finishes initializing, access the active local endpoints:

* **Platform UI (React Dashboard):** [http://localhost:5173](http://localhost:5173)

* **Platform Backend API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

* **Testbed Dashboard:** [http://localhost:8080](http://localhost:8080)

* **Network Webhook Server (Ngrok Target):** `http://localhost:9001`
