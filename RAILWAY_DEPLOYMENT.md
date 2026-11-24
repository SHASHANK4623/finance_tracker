# 🚀 Deploying MONARCH Private Wealth to Railway (`https://railway.com/new`)

This project is pre-configured for seamless 1-click deployment on [Railway](https://railway.com/new) with **Django 5.2 + Gunicorn + WhiteNoise + SQL (MySQL / PostgreSQL)**.

---

## 📋 Architecture & Included Railway Configurations

| Component | Technology | Configuration File |
| :--- | :--- | :--- |
| **WSGI Server** | Gunicorn | `Procfile` & `railway.json` |
| **Static File Serving** | WhiteNoise (`CompressedStaticFilesStorage`) | `monarch_wealth/settings.py` |
| **Database Handling** | Dynamic SQL via `dj-database-url` & `PyMySQL` | `DATABASE_URL` / `MYSQL_URL` / `MYSQLHOST` |
| **Nixpacks Build** | Python 3.12 + auto collectstatic & migrate | `nixpacks.toml` |
| **Environment Template** | Sample variables | `.env.example` |

---

## 🛠️ Step-by-Step Deployment Guide

### Step 1: Push Project to GitHub
Initialize your Git repository (if not already done) and push to GitHub:
```bash
git init
git add .
git commit -m "Configure MONARCH for Railway deployment with Gunicorn & MySQL"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo-name>.git
git push -u origin main
```

---

### Step 2: Open Railway & Create New Project
1. Navigate to **[https://railway.com/new](https://railway.com/new)**.
2. Sign in with GitHub.
3. Select **"Deploy from GitHub repo"**.
4. Choose your repository (`Django_Final_Project` or your chosen repo name).

---

### Step 3: Add a MySQL Database on Railway (1-Click)
1. In your Railway project canvas, click **"+ New"** button at the top right.
2. Select **"Database"** → Choose **"Add MySQL"** (or PostgreSQL).
3. Railway will provision a managed MySQL instance in seconds.

---

### Step 4: Link Database to Your Django App
Railway automatically sets `DATABASE_URL` and `MYSQL_URL` when linked, or you can connect them:
1. Click on your Django web service in the Railway canvas.
2. Go to the **"Variables"** tab.
3. Click **"New Variable"** → **"Add Reference"**:
   - Reference `DATABASE_URL` from the MySQL service (or click **"Add All"** MySQL variables).
4. (Optional) Set the following environment variables:
   - `DEBUG`: `False`
   - `SECRET_KEY`: `<Generate a random secure string>`
   - `ALLOWED_HOSTS`: `*`

---

### Step 5: Automatic Build & Deployment
Railway will automatically:
1. Detect Python 3.12 via `nixpacks.toml` / `runtime.txt`.
2. Install all dependencies from `requirements.txt` (including `gunicorn`, `whitenoise`, `dj-database-url`, `PyMySQL`).
3. Run `python manage.py collectstatic --noinput` to compile all luxury styling, charts, and scripts.
4. Execute `python manage.py migrate` to create all MySQL tables.
5. Launch `gunicorn monarch_wealth.wsgi:application --bind 0.0.0.0:$PORT`.

---

### Step 6: Generate Public Domain
1. In your web service settings, go to **"Settings"** → **"Networking"**.
2. Click **"Generate Domain"** (e.g., `monarch-wealth-production.up.railway.app`).
3. Open your generated domain to see MONARCH live!

---

### Step 7: Create Your First Admin User on Railway
Once deployed, open Railway's web terminal (or run via Railway CLI):
1. In Railway, click your web service → **"Deployments"** → open the latest deployment → Click **"Terminal"**.
2. Run:
   ```bash
   python manage.py createsuperuser
   ```
3. Enter your desired admin username, email, and password.
4. Now open your live web URL, go to `/login/`, sign in with those credentials, and you will be immediately directed to the **Admin User Management** console!

---

## 🔒 Unified Login Behavior

- **Administrators (`is_staff=True` or `is_superuser=True`)**:
  - Sign in directly using the regular `/login/` form.
  - Automatically routed to the **User Management Console** (`/admin-panel/users/`).
  - Full authority to create, edit, activate/deactivate, reset passwords, or inspect any user's portfolio.
  - Direct 1-click access to the native Django Admin (`/admin/`) and personal wealth dashboard.
- **Standard Wealth Members**:
  - Sign in using the same `/login/` form.
  - Routed to their personal wealth analytics dashboard (`/`).
