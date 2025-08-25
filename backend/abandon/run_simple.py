#!/usr/bin/env python3
"""
Simple backend runner to avoid uvicorn multiprocessing issues on Windows
"""
import sys
import logging
import uvicorn

# Configure logging to avoid buffer issues
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

if __name__ == "__main__":
    print("=" * 50)
    print("ALS Assistant Backend - Simple Runner")
    print("=" * 50)
    print("Starting server on http://127.0.0.1:8001")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    try:
        uvicorn.run(
            "app.main:app",
            host="127.0.0.1",
            port=8001,  # Use different port to avoid conflicts
            reload=False,  # Disable auto-reload to avoid path issues
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\nShutting down server...")
    except Exception as e:
        print(f"Server error: {e}")
        sys.exit(1)