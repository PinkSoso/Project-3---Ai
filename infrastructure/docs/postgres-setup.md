# Postgres and pgAdmin setup guide

This guide walks you through setting up the local Postgres database and pgAdmin using Docker. All the files you need are already in the repo so there is nothing to create from scratch. Follow the steps in order. The whole process takes around 15 minutes.

Before you start, make sure Docker Desktop is installed and running on your machine. If you see **Engine running** in the bottom left of Docker Desktop, you are good to go.

---

## What you need from the repo

Before running anything, make sure you have these files from the repo:

```
ab-testing-agent/
├── infrastructure/
│   └── docker-compose.yml      <-- starts Postgres and pgAdmin
├── test_db.py                  <-- confirms Python can connect
└── .env.example                <-- copy this to .env and fill in your values
```

If you have not cloned the repo yet:

```powershell
git clone https://github.com/YOUR-USERNAME/ab-testing-agent.git
cd ab-testing-agent
```

---

## Step 1 — Install Docker Desktop

If Docker Desktop is already installed and showing Engine running, skip to Step 2.

Download Docker Desktop for Windows from:

```
https://www.docker.com/products/docker-desktop
```

Run the installer and follow the prompts. When it finishes, start Docker Desktop from the Start menu and wait until the bottom left shows **Engine running**.

During installation, Docker may ask you to enable WSL 2 (Windows Subsystem for Linux). Accept this if prompted — it is required for Docker to run on Windows.

Verify Docker is working by opening PowerShell:

```powershell
docker --version
docker compose version
```

Both should return version numbers. If you see an error, make sure Docker Desktop is open before trying again.

---

## Step 2 — Set up your .env file

In the repo root, copy `.env.example` to a new file called `.env`:

```powershell
copy .env.example .env
```

Open `.env` and update the database section with the IP address of the team member hosting Postgres. They can find their IP by running `ipconfig` in PowerShell and looking for the **IPv4 Address** line under their active network adapter (usually Wi-Fi).

The lines to update are:

```
POSTGRES_HOST=192.168.1.XX        <-- replace XX with their actual IP
DATABASE_URL=postgresql://lumino:lumino@192.168.1.XX:5432/lumino
```

If you are the person hosting Postgres, leave both as `localhost`:

```
POSTGRES_HOST=localhost
DATABASE_URL=postgresql://lumino:lumino@localhost:5432/lumino
```

The `.env` file is in `.gitignore` and must never be committed to the repo. Share connection details with teammates directly, not through GitHub.

---

## Step 3 — Start the containers

Navigate to the infrastructure folder and start both containers:

```powershell
cd infrastructure
docker compose up -d
```

The `-d` flag runs the containers in the background so your terminal stays free. The first time you run this, Docker will download the Postgres and pgAdmin images which takes a minute or two depending on your connection.

You should see output ending with something like:

```
Container lumino_postgres  Started
Container lumino_pgadmin   Started
```

If your terminal appears to freeze after running the command and will not accept input, close the PowerShell window and open a new one. The containers will still be running in the background.

Verify both are running:

```powershell
docker ps
```

You should see `lumino_postgres` and `lumino_pgadmin` both listed with status **Up**. You can also check by opening Docker Desktop and clicking the Containers tab in the left sidebar.

---

## Step 4 — Access pgAdmin in your browser

Open your browser and go to:

```
http://localhost:5050
```

Log in with:

| Field | Value |
|---|---|
| Email | admin@lumino.com |
| Password | lumino |

### Register the Postgres server

Once logged in, you need to connect pgAdmin to the database. You only need to do this once.

1. Right-click **Servers** in the left panel and select **Register > Server**
2. On the **General** tab, set **Name** to `Lumino`
3. Click the **Connection** tab and fill in as follows:

| Field | Value |
|---|---|
| Host | postgres |
| Port | 5432 |
| Maintenance database | lumino |
| Username | lumino |
| Password | lumino |

The host is `postgres` (the Docker service name) not `localhost`. pgAdmin talks to Postgres from inside the Docker network, not directly from your laptop.

4. Click **Save**. The Lumino database will appear in the left panel under Servers.

---

## Step 5 — Install Python packages

Check which Python command works on your machine by trying each of these:

```powershell
python --version
python3 --version
py --version
```

Use whichever returns a version number for the commands below. If none of them work, Python is not installed. Download it from `https://www.python.org/downloads` and during installation tick **Add Python to PATH** before clicking Install Now.

Install the required packages:

```powershell
python -m pip install psycopg2-binary python-dotenv
```

---

## Step 6 — Test the connection

From the repo root, run the test script:

```powershell
python test_db.py
```

If everything is working you will see a Postgres version string followed by:

```
Connection successful
```

If you see an error, check that Docker Desktop is open, the containers are running (`docker ps`), and your `.env` file is in the repo root with the correct host IP.

---

## Day to day commands

Run these from inside the `infrastructure` folder:

```powershell
# Start both containers
docker compose up -d

# Stop both containers (your data is preserved)
docker compose down

# Stop and wipe all data — use with caution
docker compose down -v

# View logs
docker compose logs postgres
docker compose logs pgadmin
```

---

## Services and ports

| Service | URL | Purpose |
|---|---|---|
| Postgres | localhost:5432 | Database — Python connects using the DATABASE_URL in .env |
| pgAdmin | http://localhost:5050 | Browser UI to view and query the database |

---

## Troubleshooting

**pip is not recognised**
Try `python -m pip install ...` instead. If that also fails, reinstall Python and tick Add Python to PATH during installation.

**docker: command not found**
Docker Desktop is not installed or not running. Open Docker Desktop and wait for Engine running before using PowerShell.

**Terminal freezes after docker compose up -d**
Close the PowerShell window and open a new one. The containers will still be running.

**Cannot connect to Postgres from Python**
Check the `.env` file is in the repo root and that `POSTGRES_HOST` has the correct IP address. Confirm the containers are running with `docker ps`.

**pgAdmin shows a version update notice**
Run the following from the infrastructure folder:

```powershell
docker compose down
docker compose pull
docker compose up -d
```

