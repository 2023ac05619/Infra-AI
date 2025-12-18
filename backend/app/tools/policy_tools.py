"""Policy management tools"""

import json
from typing import List
from app.db import get_all_policies
from app.models import Policy


async def fetch_all_policies() -> str:
    """
    Fetch all self-healing policies from the database.
    
    Returns:
        JSON string with all policies
    """
    try:
        policies = await get_all_policies()
        
        policies_data = [
            {
                "id": p.id,
                "name": p.name,
                "condition": p.condition,
                "action": p.action,
                "priority": p.priority
            }
            for p in policies
        ]
        
        result = {
            "status": "success",
            "count": len(policies_data),
            "policies": policies_data
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        error_result = {
            "status": "error",
            "error": str(e)
        }
        return json.dumps(error_result, indent=2)
