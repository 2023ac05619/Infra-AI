#!/usr/bin/env python3
"""Initialize database tables"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import init_db


async def main():
    """Initialize database"""
    print("Initializing database...")
    
    try:
        await init_db()
        print(" Database initialized successfully!")
        print("\nTables created:")
        print("  - policies")
        print("  - system_assets")
        print("  - chat_history")
        print("  - job_logs")
    except Exception as e:
        print(f" Error initializing database: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
