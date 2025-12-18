#!/usr/bin/env python3
"""Load sample policies into the database"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import create_policy


async def load_policies():
    """Load sample policies from JSON file"""
    
    # Read sample policies
    policies_file = Path(__file__).parent / "sample_policies.json"
    
    if not policies_file.exists():
        print(f"Error: {policies_file} not found")
        return
    
    with open(policies_file, 'r') as f:
        policies = json.load(f)
    
    print(f"Loading {len(policies)} sample policies...\n")
    
    # Create each policy
    for policy_data in policies:
        try:
            policy = await create_policy(
                name=policy_data['name'],
                condition=policy_data['condition'],
                action=policy_data['action'],
                priority=policy_data.get('priority', 100)
            )
            print(f" Created policy: {policy.name} (ID: {policy.id}, Priority: {policy.priority})")
        except Exception as e:
            print(f" Failed to create policy '{policy_data['name']}': {str(e)}")
    
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(load_policies())
