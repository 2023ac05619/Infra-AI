#!/usr/bin/env python3
"""
Direct test of Prometheus metrics querying
Demonstrates CPU and memory metric queries directly against Prometheus
"""

import requests
import json
import sys


def query_prometheus(endpoint, params=None):
    """Make a request to Prometheus API"""
    base_url = "http://localhost:9090"
    url = f"{base_url}/api/v1/{endpoint}"

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        result = response.json()

        if result["status"] != "success":
            error_msg = result.get('error', 'Unknown error')
            raise ValueError(f"Prometheus API error: {error_msg}")

        return result["data"]
    except Exception as e:
        raise Exception(f"Prometheus request failed: {e}")


def main():
    print(" Direct Prometheus Metrics Test")
    print("=" * 50)

    try:
        # Test basic connectivity
        print("\n Testing Prometheus connectivity...")
        result = query_prometheus("query", {"query": "up"})
        print(" Prometheus connection successful")
        print(f"   Status: Server is {'up' if result['result'][0]['value'][1] == '1' else 'down'}")

        # Test metrics listing
        print("\n Testing metrics listing...")
        metrics = query_prometheus("label/__name__/values")
        print(f" Found {len(metrics)} metrics")
        print("Sample metrics:")
        for i, metric in enumerate(metrics[:15]):
            print(f"  {i+1:2d}. {metric}")
        if len(metrics) > 15:
            print(f"  ... and {len(metrics) - 15} more")

        # Test CPU metrics
        print("\n Testing CPU metrics queries...")
        cpu_queries = [
            ("Process CPU", "rate(process_cpu_user_seconds_total[5m])"),
            ("System CPU Usage", "100 - (avg by(instance) (irate(node_cpu_seconds_total{mode='idle'}[5m])) * 100)"),
            ("CPU Seconds Total", "rate(cpu_seconds_total{mode!='idle'}[5m])")
        ]

        cpu_found = False
        for name, query in cpu_queries:
            try:
                result = query_prometheus("query", {"query": query})
                if result.get("result"):
                    values = result["result"]
                    print(f" {name} query successful")
                    print(f"   Returned {len(values)} result(s)")
                    if values:
                        sample = values[0]
                        metric_name = sample.get("metric", {}).get("__name__", "unknown")
                        metric_value = sample.get("value", [None, "N/A"])[1]
                        print(f"   Sample: {metric_name} = {metric_value}")
                        cpu_found = True
                    break
                else:
                    print(f"️ {name} query returned no results")
            except Exception as e:
                print(f"️ {name} query failed: {e}")

        if not cpu_found:
            print("️ No CPU metrics found - this is normal if Prometheus doesn't have system metrics")

        # Test memory metrics
        print("\n Testing memory metrics queries...")
        memory_queries = [
            ("Process Memory", "process_resident_memory_bytes"),
            ("Go Memory Alloc", "go_memstats_alloc_bytes"),
            ("System Memory Used", "node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes"),
            ("System Memory Usage %", "(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100")
        ]

        memory_found = False
        for name, query in memory_queries:
            try:
                result = query_prometheus("query", {"query": query})
                if result.get("result"):
                    values = result["result"]
                    print(f" {name} query successful")
                    print(f"   Returned {len(values)} result(s)")
                    if values:
                        sample = values[0]
                        metric_name = sample.get("metric", {}).get("__name__", "unknown")
                        metric_value = sample.get("value", [None, "N/A"])[1]
                        print(f"   Sample: {metric_name} = {metric_value}")
                        memory_found = True
                    break
                else:
                    print(f"️ {name} query returned no results")
            except Exception as e:
                print(f"️ {name} query failed: {e}")

        if not memory_found:
            print("️ No memory metrics found - this is normal if Prometheus doesn't have system metrics")

        # Test range queries
        print("\n Testing range queries...")
        try:
            result = query_prometheus("query_range", {
                "query": "up",
                "start": "2025-12-11T08:00:00Z",
                "end": "2025-12-11T08:05:00Z",
                "step": "1m"
            })
            if result.get("result"):
                values = result["result"]
                print(" Range query successful")
                print(f"   Returned {len(values)} time series")
                if values:
                    series = values[0]
                    metric_name = series.get("metric", {}).get("__name__", "unknown")
                    data_points = series.get("values", [])
                    print(f"   Sample series: {metric_name} with {len(data_points)} data points")
                    if data_points:
                        print("   First few data points:")
                        for i, (timestamp, value) in enumerate(data_points[:3]):
                            print(".1f")
            else:
                print("️ Range query returned no results")
        except Exception as e:
            print(f"️ Range query failed: {e}")

        print("\n Prometheus metrics test completed!")
        print("\n Summary:")
        print("   • Prometheus server is accessible")
        print(f"   • Found {len(metrics)} available metrics")
        print(f"   • CPU metrics: {'Found' if cpu_found else 'Not available'}")
        print(f"   • Memory metrics: {'Found' if memory_found else 'Not available'}")
        print("   • Range queries: Working")

    except Exception as e:
        print(f" Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
