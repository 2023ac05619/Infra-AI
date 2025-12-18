"""Network scanning tool using nmap"""

import json
import nmap
from typing import List, Dict
from app.db import upsert_asset


async def scan_network(subnet: str = "192.168.1.0/24") -> str:
    """
    Scan a network subnet using nmap and update the asset database.
    
    Args:
        subnet: Network subnet in CIDR notation (e.g., '192.168.1.0/24')
        
    Returns:
        JSON string with scan results summary
    """
    try:
        # Initialize nmap scanner
        nm = nmap.PortScanner()
        
        # Perform scan (basic host discovery + common ports)
        print(f"[NETWORK-SCAN] Starting scan on subnet: {subnet}")
        nm.scan(hosts=subnet, arguments='-sS -sV -T4 -F')
        
        assets_found = []
        
        # Parse scan results
        for host in nm.all_hosts():
            if nm[host].state() == 'up':
                hostname = nm[host].hostname() if nm[host].hostname() else None
                services = []
                
                # Extract open ports and services
                for proto in nm[host].all_protocols():
                    ports = nm[host][proto].keys()
                    for port in ports:
                        service_name = nm[host][proto][port].get('name', 'unknown')
                        services.append(f"{port}/{proto}:{service_name}")
                
                # Determine asset type (simple heuristic)
                asset_type = "server"
                if any('http' in s for s in services):
                    asset_type = "vm"
                
                # Upsert to database
                asset = await upsert_asset(
                    ip=host,
                    hostname=hostname,
                    asset_type=asset_type,
                    services=services
                )
                
                assets_found.append({
                    "ip": asset.ip,
                    "hostname": asset.hostname,
                    "type": asset.type,
                    "services": asset.services
                })
        
        result = {
            "status": "success",
            "subnet": subnet,
            "hosts_found": len(assets_found),
            "assets": assets_found
        }
        
        print(f"[NETWORK-SCAN] Completed. Found {len(assets_found)} hosts.")
        return json.dumps(result, indent=2)
        
    except Exception as e:
        error_result = {
            "status": "error",
            "subnet": subnet,
            "error": str(e)
        }
        print(f"[NETWORK-SCAN] Error: {str(e)}")
        return json.dumps(error_result, indent=2)
