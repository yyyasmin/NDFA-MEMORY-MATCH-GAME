# Deploy Backend to Render (Step by Step)

Your repo: `https://github.com/yyyasmin/NDFA-MEMORY-MATCH-GAME`

---

## 1. Create a Render account

- Go to [https://render.com](https://render.com) and sign up (free).
- Log in.

---

## 2. Create a PostgreSQL database

1. In the dashboard, click **New +** → **PostgreSQL**.
2. Set:
   - **Name:** `ndfa-memory-db` (or any name).
   - **Region:** choose closest to you.
   - **Plan:** **Free**.
3. Click **Create Database**.
4. Wait until the DB is **Available**.
5. Open the database → **Info** (or **Connections**).
6. Copy **Internal Database URL** (starts with `postgresql://`).  
   You will use it as `DATABASE_URL` for the backend.  
   (Internal URL works for a web service in the same Render account.)

---

## 3. Create the Web Service (backend)

1. Click **New +** → **Web Service**.
2. **Connect repository:**
   - If GitHub is not connected, click **Connect account** and authorize Render.
   - Select **yyyasmin/NDFA-MEMORY-MATCH-GAME**.
3. Configure the service:
   - **Name:** `ndfa-memory-backend` (or any name).
   - **Region:** same as the DB (or closest).
   - **Branch:** `main` (or the branch you push to).
   - **Root Directory:** type **`backend`** (important).
   - **Runtime:** **Python 3**.
   - **Build Command:**  
     `pip install -r requirements.txt && python db_create.py --init`  
     (installs deps and creates DB tables if missing; safe, no data loss)
   - **Start Command:**  
     `gunicorn -w 1 --threads 100 -b 0.0.0.0:$PORT app:app`
4. **Environment variables:**
   - Click **Add Environment Variable**.
   - **Key:** `DATABASE_URL`  
   - **Value:** paste the **Internal Database URL** you copied from the PostgreSQL service.
   - (Optional) **Key:** `CORS_ORIGINS`  
     **Value:** your Netlify frontend URL, e.g. `https://your-app.netlify.app`  
     (You can add this later when the frontend is on Netlify.)
5. **Plan:** **Free**.
6. Click **Create Web Service**.

Render will clone the repo, run the build command in the `backend` folder, then start the app. Wait until the service shows **Live** (green).

---

## 4. Get your backend URL

- In the web service page, at the top you’ll see something like:  
  **https://ndfa-memory-backend.onrender.com**
- Copy this URL. You will use it when deploying the frontend on Netlify (for API and Socket.IO).

---

## 5. Create tables in the database

If you set **Pre-Deploy Command** to `python db_create.py --init`, Render runs it before each deploy and creates tables if they don't exist (no drop, safe for production).

**Optional – Run locally once with production DB** (only if you did not use Pre-Deploy)

1. In Render: PostgreSQL → **Info** → copy **External Database URL** (if you need to connect from your PC).
2. On your PC, in the project folder, create or edit `backend/.env` and set:
   ```env
   DATABASE_URL=<paste External Database URL>
   ```
3. From the project root:
   ```bash
   cd backend
   python db_create.py
   ```
4. After tables are created, you can remove or leave the External URL in `.env` (do not commit `.env`).

**Option B – Add a one-off “build” step (optional)**

Some people add a release command that runs migrations or `db_create`. For this project, running `db_create.py` once (Option A) is enough.

---

## 6. Check that the backend works

- Open in the browser: **https://YOUR-SERVICE-NAME.onrender.com/api/health**  
  You should see something like: `{"status":"ok"}`.
- If that works, the backend is deployed.

---

## 7. (Later) Connect Netlify frontend

When you deploy the frontend on Netlify:

1. Set the backend base URL in the frontend (e.g. with an env var like `VITE_API_URL` or similar), e.g.  
   `https://ndfa-memory-backend.onrender.com`
2. In Render, for the backend service, add or set:
   - **CORS_ORIGINS** = your Netlify URL, e.g. `https://your-app.netlify.app`  
   so the browser allows requests from the frontend to the backend.

---

## Troubleshooting

- **Build fails:** Make sure **Root Directory** is `backend` and **Build Command** is `pip install -r requirements.txt`.
- **Service crashes / “Application failed to respond”:** Check **Logs** in the Render service. Ensure **Start Command** is: `gunicorn -w 1 --threads 100 -b 0.0.0.0:$PORT app:app`
- **Database connection error:** Check that `DATABASE_URL` is the **Internal Database URL** from the PostgreSQL service (not External, unless you run `db_create.py` from your PC with External URL).
- **Free tier:** The service may “spin down” after inactivity; the first request after that can take 30–60 seconds.
