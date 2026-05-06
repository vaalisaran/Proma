# Deployment Guide for PythonAnywhere

This guide explains how to deploy the Django and Radicale servers to PythonAnywhere.

## 1. Prepare GitHub
1. Create a new repository on GitHub.
2. Initialize git in your project directory:
   ```bash
   git init
   git add .
   git commit -m "Initial commit for deployment"
   git remote add origin YOUR_GITHUB_REPO_URL
   git push -u origin main
   ```

---

## 2. Deploy Django Server (vmgbhss.pythonanywhere.com)

1. **Create Web App**:
   - Go to the **Web** tab on PythonAnywhere.
   - Click **Add a new web app**.
   - Choose **Manual Configuration** (don't choose Django).
   - Select **Python 3.10**.

2. **Clone Code**:
   - Open a **Bash Console** and run:
     ```bash
     git clone YOUR_GITHUB_REPO_URL
     cd IIA_Managementv3
     ```

3. **Set up Virtual Environment**:
   ```bash
   mkvirtualenv --python=/usr/bin/python3.10 venv_django
   pip install -r requirements.txt
   ```

4. **Configure Web App**:
   - **Source code**: `/home/YOUR_USERNAME/IIA_Managementv3`
   - **Working directory**: `/home/YOUR_USERNAME/IIA_Managementv3`
   - **Virtualenv**: `/home/YOUR_USERNAME/.virtualenvs/venv_django`

5. **Static & Media Files**:
   - In the **Web** tab, under **Static files**:
     - URL: `/static/`, Directory: `/home/YOUR_USERNAME/IIA_Managementv3/staticfiles/`
     - URL: `/media/`, Directory: `/home/YOUR_USERNAME/IIA_Managementv3/media/`
   - Run `python manage.py collectstatic` in your console.

6. **Google OAuth (Optional)**:
   - If using Google Calendar sync, update your Redirect URIs in [Google Cloud Console](https://console.cloud.google.com/):
     - Authorized redirect URIs: `https://vmgbhss.pythonanywhere.com/calendar/google/callback/`
     - Authorized JavaScript origins: `https://vmgbhss.pythonanywhere.com`
   - Download the new `client_secret.json` and replace the one in your project folder.

7. **WSGI Configuration**:
   - Click on the WSGI configuration file link.
   - Replace its content with the contents of `django_wsgi.py`.
   - Update `path` in the file if your folder name is different.

8. **Database**:
   - Run `python manage.py migrate`.
   - Create a superuser: `python manage.py createsuperuser`.

---

## 3. Deploy Radicale Server (ssaran.pythonanywhere.com)

1. **Create Web App**:
   - Go to the **Web** tab on PythonAnywhere.
   - Click **Add a new web app**.
   - Choose **Manual Configuration**.
   - Select **Python 3.10**.

2. **Set up Virtual Environment**:
   - Open a **Bash Console**:
     ```bash
     mkvirtualenv --python=/usr/bin/python3.10 venv_radicale
     pip install radicale passlib
     ```

3. **Configure Web App**:
   - **Source code**: `/home/YOUR_USERNAME/IIA_Managementv3`
   - **Virtualenv**: `/home/YOUR_USERNAME/.virtualenvs/venv_radicale`

4. **WSGI Configuration**:
   - Click on the WSGI configuration file link.
   - Replace its content with the contents of `radicale_wsgi.py`.
   - Ensure `path` points to your project folder.

5. **Configuration File**:
   - Ensure `radicale.conf` and `radicale_users.htpasswd` are in the project folder.
   - `radicale.conf` is already configured to look for `./radicale_data`.

---

## 4. Final Steps
- Reload both web apps from the **Web** tab.
- In your Django app, go to user settings and set the CalDAV URL to `https://ssaran.pythonanywhere.com/`.
