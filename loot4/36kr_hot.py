#!/usr/bin/env python3
"""Fetch 36kr hot list and print top 15 titles."""

import requests
import json
import sys

def fetch_36kr_hot(top_n=15):
    url = "https://gateway.36kr.com/api/mis/nav/home/nav/rank/hot"
    payload = {
        "partner_id": "wap",
        "param": {
            "siteId": 1,
            "platformId": 2
        }
    }
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://36kr.com/",
        "Origin": "https://36kr.com"
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    # Navigate the response structure to extract hot items
    items = []
    if data.get("code") == 0 or data.get("statusCode") == 0:
        result = data.get("data", {})
        # Try various known response structures
        hot_list = (
            result.get("hotRankList", [])
            or result.get("itemList", [])
            or result.get("list", [])
            or result.get("hotList", [])
            or result
        )
        if isinstance(hot_list, list):
            for entry in hot_list[:top_n]:
                title = (
                    entry.get("title", "")
                    or entry.get("templateMaterial", {}).get("widgetTitle", "")
                    or entry.get("name", "")
                    or str(entry)
                )
                items.append(title)
        elif isinstance(hot_list, dict):
            # Might be nested further
            for key in hot_list:
                if isinstance(hot_list[key], list):
                    for entry in hot_list[key][:top_n]:
                        title = (
                            entry.get("title", "")
                            or entry.get("templateMaterial", {}).get("widgetTitle", "")
                            or entry.get("name", "")
                            or str(entry)
                        )
                        items.append(title)
                    break
    else:
        # Fallback: dump keys for debugging
        print(f"Unexpected response code: {data.get('code')}, statusCode: {data.get('statusCode')}")
        print(f"Top-level keys: {list(data.keys())}")
        if data.get("data"):
            print(f"Data keys: {list(data['data'].keys()) if isinstance(data['data'], dict) else type(data['data'])}")
        return []

    return items[:top_n]


if __name__ == "__main__":
    try:
        titles = fetch_36kr_hot(15)
        if titles:
            print("=== 36Kr Hot List Top 15 ===")
            for i, title in enumerate(titles, 1):
                print(f"{i:2d}. {title}")
        else:
            print("No items found or unexpected API response.")
            # Print raw response for debugging
            resp = requests.post(
                "https://gateway.36kr.com/api/mis/nav/home/nav/rank/hot",
                json={"partner_id": "wap", "param": {"siteId": 1, "platformId": 2}},
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            print(json.dumps(resp.json(), ensure_ascii=False, indent=2)[:3000])
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
