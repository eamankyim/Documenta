# 🚀 **DEPLOY TO RENDER - FIX BAD GATEWAY**

## 🚨 **IMMEDIATE ACTION REQUIRED**

Your app is working locally but failing on Render. Follow these steps **EXACTLY**:

## 📋 **Step 1: Verify Files Are Ready**

Ensure these files exist and are committed to your repository:
- ✅ `wsgi.py` - New WSGI entry point
- ✅ `render.yaml` - Render configuration
- ✅ `render-requirements.txt` - Production dependencies
- ✅ `Procfile` - Alternative deployment method

## 🔧 **Step 2: Force Redeploy on Render**

1. **Go to [Render Dashboard](https://dashboard.render.com)**
2. **Click on your `documenta` service**
3. **Click "Manual Deploy" button**
4. **Choose "Clear build cache & deploy"**
5. **Wait for deployment to complete**
6. **Check the "Logs" tab for errors**

## 📊 **Step 3: Monitor Deployment Logs**

Look for these specific error messages:

### **✅ SUCCESS INDICATORS:**
```
✅ Installing dependencies...
✅ Building application...
✅ Starting application...
✅ Service is live
```

### **❌ ERROR INDICATORS:**
```
❌ ModuleNotFoundError: No module named 'flask'
❌ ImportError: cannot import name 'db'
❌ Database connection failed
❌ Port already in use
```

## 🆘 **Step 4: If Still Getting Bad Gateway**

### **Option A: Use Procfile Instead**
1. Delete `render.yaml` from your repo
2. Keep `Procfile` with: `web: python wsgi.py`
3. Redeploy

### **Option B: Check Environment Variables**
Ensure these are set in Render:
```
DATABASE_URL=postgresql://splitter_user:Sb74paNPJ8M5FpopNYwVSJQvVwLcJBev@dpg-d2e6aobe5dus73fjrtc0-a.oregon-postgres.render.com/splitter_db
SECRET_KEY=your-secret-key-here
FLASK_ENV=production
FLASK_DEBUG=0
```

### **Option C: Downgrade Python Version**
In Render dashboard:
1. Go to Environment
2. Set `PYTHON_VERSION` to `3.11.0`

## 🔍 **Step 5: Test After Deployment**

1. **Wait 2-3 minutes after deployment completes**
2. **Visit your service URL**
3. **Test the health endpoint**: `https://documenta.onrender.com/health`
4. **Check if you can log in**
5. **Verify projects are still there**

## 📞 **Step 6: Get Help if Needed**

If still failing:
1. **Copy the exact error from Render logs**
2. **Share the error message**
3. **Include your service URL**

## 🎯 **Expected Result**

After successful deployment:
- ✅ Service shows "Live" status
- ✅ Health endpoint returns JSON response
- ✅ You can access your app normally
- ✅ Projects persist between deployments

---

**Remember**: The key is using `wsgi.py` as the entry point and ensuring all dependencies are correctly specified in `render-requirements.txt`.
