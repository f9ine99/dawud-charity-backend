#!/usr/bin/env python3
"""
Dawud Charity Hub - Production Startup Script for cPanel
Run this script to start the application in production mode on cPanel
"""

import uvicorn
import os
import sys
from pathlib import Path

def main():
    """Start the Dawud Charity Hub application for cPanel deployment."""

    # Change to backend directory if not already there
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)

    # Get port from environment or use default (cPanel typically assigns ports)
    port = int(os.getenv("PORT", 8000))

    # Get host from environment or use default
    host = os.getenv("HOST", "0.0.0.0")

    print("🚀 Starting Dawud Charity Hub Donation System...")
    print(f"📍 Host: {host}")
    print(f"🔌 Port: {port}")
    print(f"📁 Working directory: {backend_dir}")
    print("📊 Admin Panel: https://admin.furi-cadaster.com/admin"
    print("🔗 API Base: https://admin.furi-cadaster.com/api"

    # Check if .env file exists
    env_file = backend_dir / ".env"
    if not env_file.exists():
        print("⚠️  Warning: .env file not found. Using default configuration.")
        print("   Consider creating a .env file with your configuration.")

    # Start the server for production
    try:
        uvicorn.run(
            "main:app",
            host=host,
            port=port,
            reload=False,  # Disable reload in production
            access_log=True,
            log_level="info",
            # Security settings for production
            ssl_keyfile=None,
            ssl_certfile=None,
            # Performance optimizations for cPanel
            workers=1,  # cPanel typically handles load balancing
            loop="asyncio",
            # Additional production security settings
            server_header=False,  # Hide server info for security
            date_header=False,    # Hide date header for security
            # Production optimizations
            backlog=2048,         # Increase backlog for better performance
            timeout_keep_alive=30,  # Keep alive timeout
            # Error handling
            log_config=None,      # Use default logging config
        )
    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
