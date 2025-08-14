# 🚀 Deployment Guide - Prevent Data Loss & Keep Service Active

## ⚠️ **CRITICAL: Preventing Data Loss on Render Free Tier**

### **Problem:**
- **Free tier services don't persist data between deployments**
- **Database gets recreated on every update**
- **Your projects disappear after each deployment**

### **Solution: Use External PostgreSQL Database**

## 📋 **Step-by-Step Setup**

### **1. Database Setup (Already Done ✅)**
Your PostgreSQL database is already configured:
- **Host**: `dpg-d2e6aobe5dus73fjrtc0-a.oregon-postgres.render.com`
- **Database**: `splitter_db`
- **User**: `splitter_user`
- **Password**: `Sb74paNPJ8M5FpopNYwVSJQvVwLcJBev`

### **2. Environment Variables**
Ensure these are set in Render:
```bash
DATABASE_URL=postgresql://splitter_user:Sb74paNPJ8M5FpopNYwVSJQvVwLcJBev@dpg-d2e6aobe5dus73fjrtc0-a.oregon-postgres.render.com/splitter_db
SECRET_KEY=your-secret-key-here
FLASK_ENV=production
FLASK_DEBUG=0
```

### **3. Deploy with render.yaml**
Use the new `render.yaml` file for proper configuration:
```bash
# In Render dashboard, connect your GitHub repo
# Render will automatically use render.yaml
```

## 🔄 **Keeping Service Active (Free Tier Sleep Issue)**

### **Option 1: Run Keep-Alive Script Locally**
```bash
# Install requirements
pip install requests schedule

# Run keep-alive script
python keep_alive.py
```

### **Option 2: Use UptimeRobot (Free)**
1. Go to [UptimeRobot.com](https://uptimerobot.com)
2. Create free account
3. Add new monitor:
   - **URL**: `https://documenta.onrender.com/health`
   - **Type**: HTTP(s)
   - **Interval**: 5 minutes
   - **Alert**: Email notifications

### **Option 3: Use Cron Job (Linux/Mac)**
```bash
# Add to crontab (runs every 10 minutes)
*/10 * * * * curl -s https://documenta.onrender.com/health > /dev/null
```

## 🚨 **Before Each Deployment**

### **1. Backup Your Data**
```bash
# Export current projects (if you have access)
curl "https://documenta.onrender.com/api/projects?token=YOUR_TOKEN"
```

### **2. Verify Database Connection**
- Check that `DATABASE_URL` is set correctly
- Ensure PostgreSQL service is running
- Test connection before deploying

### **3. Deploy Safely**
- Use `render.yaml` configuration
- Monitor deployment logs
- Verify data persistence after deployment

## 📊 **Monitoring & Verification**

### **Health Check Endpoint**
- **URL**: `https://documenta.onrender.com/health`
- **Purpose**: Verify service is running
- **Response**: JSON with status and timestamp

### **Database Verification**
After deployment, check:
1. Can you log in?
2. Are your projects still there?
3. Can you create new projects?

## 🆘 **If Data is Lost**

### **Recovery Steps:**
1. **Check Database Connection**: Verify `DATABASE_URL` is correct
2. **Check Render Logs**: Look for database connection errors
3. **Verify Tables Exist**: Check if database schema was created
4. **Contact Support**: If persistent issues

### **Prevention for Future:**
- Always use external PostgreSQL database
- Never rely on Render's ephemeral storage
- Test deployments on staging first
- Keep regular backups

## 🔧 **Troubleshooting**

### **Common Issues:**
1. **"Database not found"**: Check `DATABASE_URL` format
2. **"Connection refused"**: Verify PostgreSQL service is running
3. **"Table doesn't exist"**: Check if `db.create_all()` ran successfully

### **Debug Commands:**
```bash
# Check database connection
python -c "from app import app, db; print(db.engine.url)"

# Check tables
python -c "from app import app, db; print(db.engine.table_names())"
```

## 📞 **Support**

If you continue to lose data:
1. Check Render deployment logs
2. Verify environment variables
3. Test database connection manually
4. Consider upgrading to paid tier for persistent storage

---

**Remember**: Free tier services are designed for development/testing, not production use with critical data. Consider upgrading to a paid plan for production applications.
