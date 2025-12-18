#!/usr/bin/env python3
"""Test self-healing engine with sample alerts"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models import PrometheusAlert
from app.core.self_healing import evaluate_alert


# Sample alerts
SAMPLE_ALERTS = [
    {
        "name": "Pod Crash Loop",
        "alert": {
            "status": "firing",
            "alerts": [
                {
                    "labels": {
                        "alertname": "PodCrashLoop",
                        "pod_name": "web-app-123",
                        "namespace": "production",
                        "severity": "critical"
                    },
                    "annotations": {
                        "summary": "Pod is crash looping",
                        "description": "The pod has restarted 5 times"
                    }
                }
            ]
        }
    },
    {
        "name": "High CPU Usage",
        "alert": {
            "status": "firing",
            "alerts": [
                {
                    "labels": {
                        "alertname": "HighCPUUsage",
                        "deployment": "api-server",
                        "namespace": "production",
                        "severity": "warning"
                    },
                    "annotations": {
                        "summary": "CPU usage is high",
                        "description": "CPU usage above 80%"
                    }
                }
            ]
        }
    },
    {
        "name": "Service Down",
        "alert": {
            "status": "firing",
            "alerts": [
                {
                    "labels": {
                        "alertname": "ServiceDown",
                        "vm_name": "db-server-01",
                        "service_type": "critical"
                    },
                    "annotations": {
                        "summary": "Critical service is down"
                    }
                }
            ]
        }
    },
    {
        "name": "Unknown Alert",
        "alert": {
            "status": "firing",
            "alerts": [
                {
                    "labels": {
                        "alertname": "RandomAlert",
                        "severity": "info"
                    },
                    "annotations": {}
                }
            ]
        }
    }
]


async def test_alerts():
    """Test alert evaluation"""
    
    print("Testing Self-Healing Engine")
    print("=" * 50)
    print()
    
    for sample in SAMPLE_ALERTS:
        print(f"Testing: {sample['name']}")
        print("-" * 50)
        
        # Create alert object
        alert = PrometheusAlert(**sample['alert'])
        
        # Evaluate alert
        action = await evaluate_alert(alert)
        
        if action:
            print(f" Action matched!")
            print(f"  Policy: {action.get('policy_name')}")
            print(f"  Tool: {action.get('tool')}")
            print(f"  Params: {json.dumps(action.get('params', {}), indent=4)}")
        else:
            print(" No matching policy found")
        
        print()


if __name__ == "__main__":
    asyncio.run(test_alerts())
