# Deploying the Exam & Academy Platform to Render

Render is the ideal host for this Django monolith: it provides real persistent containers, managed PostgreSQL, free HTTPS dev domains (`https://<your-app>.onrender.com`), and automatic deployments on every `git push`.

---

## Method 1: 1-Click Blueprint Deploy (Fastest & Recommended)

This repository includes a [`render.yaml`](file:///d:/Projects/EXAM_PLATFORM/render.yaml) blueprint file that automatically provisions both your **PostgreSQL database** and your **Web Service** with all required environment variables wired together.

1. **Push your code to GitHub:**
   ```bash
   git add .
   git commit -m "Configure production deployment for Render"
   git push origin main
   ```

2. **Open Render Dashboard:**
   * Go to [dashboard.render.com](https://dashboard.render.com).
   * Click the **New +** button in the top right and select **Blueprint**.
   * Connect your GitHub account and select your repository (`EXAM_PLATFORM`).

3. **Deploy:**
   * Render will detect `render.yaml` and show:
     - **PostgreSQL Database:** `exam-platform-db`
     - **Web Service:** `exam-platform`
   * Click **Apply**.
   * Render will automatically:
     - Spin up the managed PostgreSQL database.
     - Build the Docker container.
     - Auto-generate a secure `SECRET_KEY` and `DEV_ADMIN_PASSWORD`.
     - Wire `DATABASE_URL` directly from the database into the web service.
     - Run `python manage.py migrate` and `python manage.py ensure_admin` on startup.
     - Assign your free live URL: `https://exam-platform-xxxx.onrender.com`.

---

## Method 2: Manual Setup via Render Dashboard

If you prefer to create the services individually:

### 1. Create the PostgreSQL Database
1. In Render, click **New +** -> **PostgreSQL**.
2. Name: `exam-platform-db`
3. Database: `drone_exams`
4. User: `postgres`
5. Plan: **Free** (or Starter for production).
6. Click **Create Database**.
7. Once created, copy the **Internal Database URL** (e.g. `postgres://postgres:...@dpg-...-a/drone_exams`).

### 2. Create the Web Service
1. Click **New +** -> **Web Service** -> select your repo.
2. Runtime: **Docker**.
3. Plan: **Free** (or Starter).
4. In the **Environment Variables** section, add:
   * `DEBUG` = `0`
   * `SECRET_KEY` = *(Click "Generate" or paste a random string)*
   * `DATABASE_URL` = *(Paste the Internal Database URL from step 1)*
   * `TIME_ZONE` = `Africa/Harare`
   * `DEV_ADMIN_USERNAME` = `admin`
   * `DEV_ADMIN_PASSWORD` = `YourStrongAdminPassword`
   * `DEV_ADMIN_EMAIL` = `admin@africadronekings.com`
   * `RESEND_API_KEY` = *(Optional: your Resend key for transactional emails)*
   * `DEFAULT_FROM_EMAIL` = `Africa Drone Kings <training@africadronekings.com>`
   * `PUBLIC_SIGNUP` = `1`
5. Click **Create Web Service**.

---

## Admin Login Credentials

When the web service launches, [`entrypoint.sh`](file:///d:/Projects/EXAM_PLATFORM/entrypoint.sh) runs:
* `python manage.py migrate --noinput`
* `python manage.py ensure_admin`

Your superuser account will be ready immediately:
* **Username:** `admin` (or whatever you set for `DEV_ADMIN_USERNAME`)
* **Password:** The value of `DEV_ADMIN_PASSWORD` (if using Blueprint, check your Web Service's **Environment** tab in Render to see the auto-generated password).
* **Admin URL:** `https://<your-service>.onrender.com/admin/`

---

## File Uploads & Media Storage Options

Because this is a real Linux container, you have two flexible storage options:

### Option A: Render Persistent Disk (Simplest, Zero External Services)
* On Render's **Starter** plan ($7/mo), you can attach a persistent disk in the dashboard:
  * Mount Path: `/app/media`
  * Size: 1 GB (or more)
* All uploaded exam questions, diagrams, and lesson files will stay permanently on disk without needing MinIO or S3.

### Option B: Cloud Object Storage (MinIO or AWS S3 / Cloudflare R2)
* If using the Free tier or cloud object storage, simply add these variables in Render:
  * `AWS_STORAGE_BUCKET_NAME` = your bucket name
  * `AWS_ACCESS_KEY_ID` = your key
  * `AWS_SECRET_ACCESS_KEY` = your secret
  * `AWS_S3_ENDPOINT_URL` = your endpoint (e.g. `https://minio.yourdomain.com` or `https://<id>.r2.cloudflarestorage.com`)
  * `AWS_S3_REGION_NAME` = `us-east-1`
