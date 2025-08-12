# Deploy Documenta to Render

## Simple Steps:

### 1. Go to Render.com
- Sign up/Login
- Click "New +" → "Web Service"

### 2. Connect GitHub
- Connect your GitHub account
- Select repository: `eamankyim/Documenta`
- Select branch: `main`

### 3. Configure Service
- **Name:** `documenta` (or whatever you want)
- **Environment:** `Python 3`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `python app.py`

### 4. Set Environment Variables
Click "Environment" tab and add:
```
SECRET_KEY=your-secret-key-here
FLASK_ENV=production
FLASK_DEBUG=0
```

### 5. Deploy!
- Click "Create Web Service"
- Wait for build to complete
- Your app will be live at: `https://your-app-name.onrender.com`

## What Gets Uploaded:
✅ All your code  
✅ `outputs/users.json` (your user accounts)  
✅ `outputs/tokens.json` (document tokens)  
✅ `templates/` (all your HTML pages)  
✅ Everything else  

## Login Credentials:
Use the same email/password you created locally!

## Notes:
- Render will automatically restart your app if it crashes
- Free tier has some limitations but works great for 2 users
- Your data (users, documents) will persist
