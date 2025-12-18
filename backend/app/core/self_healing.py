"""Self-Healing Engine - Policy Evaluator"""

import json
from typing import Optional, Dict, Any
from app.models import PrometheusAlert, Policy
from app.db import get_all_policies


async def evaluate_alert(alert: PrometheusAlert) -> Optional[Dict[str, Any]]:
    """
    Evaluate a Prometheus alert against all policies.
    
    Args:
        alert: Prometheus alert webhook payload
        
    Returns:
        Action dictionary if a policy matches, None otherwise
    """
    # Fetch all policies sorted by priority
    policies = await get_all_policies()
    
    if not policies:
        print("[SELF-HEALING] No policies found")
        return None
    
    # Extract alert information
    alert_status = alert.status
    
    # Process each alert in the payload
    for alert_item in alert.alerts:
        labels = alert_item.get("labels", {})
        annotations = alert_item.get("annotations", {})
        
        print(f"[SELF-HEALING] Evaluating alert: {labels.get('alertname', 'unknown')}")
        
        # Check against each policy
        for policy in policies:
            if _match_condition(policy.condition, labels, annotations, alert_status):
                print(f"[SELF-HEALING] Policy matched: {policy.name} (priority: {policy.priority})")
                
                # Prepare action with context from alert
                action = policy.action.copy()
                action["policy_name"] = policy.name
                action["alert_labels"] = labels
                
                # Interpolate parameters from alert labels
                if "params" in action:
                    action["params"] = _interpolate_params(action["params"], labels, annotations)
                
                return action
    
    print("[SELF-HEALING] No matching policy found")
    return None


def _match_condition(condition: Dict[str, Any], labels: Dict[str, Any], annotations: Dict[str, Any], status: str) -> bool:
    """
    Check if a policy condition matches the alert.
    
    Args:
        condition: Policy condition dictionary
        labels: Alert labels
        annotations: Alert annotations
        status: Alert status ("firing" or "resolved")
        
    Returns:
        True if condition matches, False otherwise
    """
    # Support multiple condition formats
    
    # Format 1: Simple label matching
    # {"label": "alertname", "value": "PodCrashLoop"}
    if "label" in condition and "value" in condition:
        label_key = condition["label"]
        expected_value = condition["value"]
        actual_value = labels.get(label_key) or annotations.get(label_key)
        return actual_value == expected_value
    
    # Format 2: Multiple label conditions
    # {"labels": {"alertname": "HighMemory", "severity": "critical"}}
    if "labels" in condition:
        for key, value in condition["labels"].items():
            if labels.get(key) != value:
                return False
        return True
    
    # Format 3: Status condition
    # {"status": "firing"}
    if "status" in condition:
        return status == condition["status"]
    
    # Format 4: Complex expression (future enhancement)
    # {"expression": "labels.severity == 'critical' and status == 'firing'"}
    if "expression" in condition:
        try:
            # Simplified evaluation (in production, use a safe evaluator)
            context = {"labels": labels, "annotations": annotations, "status": status}
            # For now, just return False - this would need safe evaluation
            return False
        except Exception:
            return False
    
    return False


def _interpolate_params(params: Dict[str, Any], labels: Dict[str, Any], annotations: Dict[str, Any]) -> Dict[str, Any]:
    """
    Interpolate parameters using alert labels and annotations.
    
    Args:
        params: Action parameters with placeholders
        labels: Alert labels
        annotations: Alert annotations
        
    Returns:
        Interpolated parameters
    """
    result = {}
    
    for key, value in params.items():
        if isinstance(value, str):
            # Replace placeholders like ${label.pod_name} or ${annotation.summary}
            if "${label." in value:
                label_key = value.split("${label.")[1].split("}")[0]
                result[key] = labels.get(label_key, value)
            elif "${annotation." in value:
                annotation_key = value.split("${annotation.")[1].split("}")[0]
                result[key] = annotations.get(annotation_key, value)
            else:
                result[key] = value
        else:
            result[key] = value
    
    return result
