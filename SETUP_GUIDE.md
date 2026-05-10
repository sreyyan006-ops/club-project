# HP Clubs – Deployment Guide
## GitHub + Render (free, no install needed)

---

## STEP 1 — Create a GitHub account
1. Go to https://github.com and sign up (free)
2. Click **New repository** (the + button top right)
3. Name it: `hp-clubs`
4. Set it to **Public**
5. Click **Create repository**

---

## STEP 2 — Upload your files to GitHub
In your new empty repo, click **uploading an existing file**

Upload ALL of these files (keep the folder structure):
```
app.py
requirements.txt
Procfile
.gitignore
templates/base.html
templates/index.html
templates/clubs.html
templates/login.html
templates/signup.html
templates/student_dashboard.html
templates/admin_dashboard.html
```

> For the templates folder: GitHub lets you drag and drop entire folders.
> Just drag the whole `templates/` folder in.

Click **Commit changes**

---

## STEP 3 — Create a Render account
1. Go to https://render.com and sign up with your GitHub account
2. This links them together automatically

---

## STEP 4 — Create a PostgreSQL database on Render
1. In Render dashboard, click **New +** → **PostgreSQL**
2. Name: `hp-clubs-db`
3. Plan: **Free**
4. Click **Create Database**
5. Wait ~1 minute for it to provision
6. Copy the **Internal Database URL** — you'll need it in Step 5

---

## STEP 5 — Deploy your web app on Render
1. Click **New +** → **Web Service**
2. Connect your `hp-clubs` GitHub repo
3. Fill in the settings:
   - **Name**: hp-clubs
   - **Runtime**: Python 3
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `gunicorn app:app`
   - **Plan**: Free
4. Click **Advanced** → **Add Environment Variable**
   - Key: `DATABASE_URL`  
     Value: paste the Internal Database URL from Step 4
   - Key: `SECRET_KEY`  
     Value: type any random string (e.g. `mrsS-clubs-2024-secret`)
5. Click **Create Web Service**
6. Render will build and deploy — takes ~2 minutes

---

## STEP 6 — You're live!
Render gives you a URL like: `https://hp-clubs.onrender.com`

**Default admin login:**
- Username: `admin`
- Password: `admin123`
⚠️ Change the admin password after first login!

---

## How to make code changes later
1. Edit the file on GitHub (click the file → pencil icon)
2. Commit the change
3. Render auto-deploys within ~1 minute

---

## Admin workflow (Mrs. S)
1. Log in at `/login` with admin credentials
2. Go to Admin Dashboard
3. Toggle **Sign-ups live** → ON (students can now submit)
4. Wait for students to submit their choices
5. Click **Run smart assign**
6. Toggle **Results published** → ON (students see their club)
7. Click **Export CSV** to download Masterlist.csv

---

## Notes for your IA
- Platform: Browser-based, works on laptops, tablets (iPads), phones
- Language: Python (Flask)
- Database: PostgreSQL (via Render free tier)
- Handles 1,000 student records easily within Render's free limits
- Response time well under 1.5s for all queries
