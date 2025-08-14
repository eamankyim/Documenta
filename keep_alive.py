#!/usr/bin/env python3
"""
Keep-alive script for Render free tier service.
This script pings your service every 10 minutes to keep it active.
Run this on your local machine or a free service like UptimeRobot.
"""

import requests
import time
import schedule
from datetime import datetime

# Your Render service URL
SERVICE_URL = "https://documenta.onrender.com"

def ping_service():
    """Ping the service to keep it active"""
    try:
        response = requests.get(f"{SERVICE_URL}/health", timeout=30)
        if response.status_code == 200:
            print(f"✅ [{datetime.now()}] Service is healthy: {response.json()}")
        else:
            print(f"⚠️  [{datetime.now()}] Service responded with status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ [{datetime.now()}] Failed to ping service: {e}")

def main():
    print(f"🚀 Starting keep-alive service for {SERVICE_URL}")
    print("📡 Will ping every 10 minutes to keep service active")
    print("⏰ Service will stay active as long as this script runs")
    print("=" * 60)
    
    # Schedule ping every 10 minutes
    schedule.every(10).minutes.do(ping_service)
    
    # Initial ping
    ping_service()
    
    # Keep running and executing scheduled tasks
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main()
