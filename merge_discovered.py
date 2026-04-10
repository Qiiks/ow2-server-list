#!/usr/bin/env python3
"""
merge_discovered.py — Merge discovered IPs into ow2-servers.json
=============================================================

Merges IPs from the OW2 Connection Logger's discovered_ow2_ips.txt log
into the ow2-servers.json file. Supports both CLI input and drag-and-drop
by accepting a log file path.

Usage:
    python merge_discovered.py                                        # Uses default log path
    python merge_discovered.py path/to/discovered_ow2_ips.txt        # Custom log path
    python merge_discovered.py --list                                # List pending IPs
    python merge_discovered.py --dry-run                             # Preview without writing
    python merge_discovered.py --ip 137.221.80.99 --region OW2-EU   # Add single IP manually

Output: Updated ow2-servers.json
"""

import json
import argparse
import re
import ipaddress
from datetime import datetime, timezone
from pathlib import Path

# Default OW2 Connection Logger discovery log location
# Default OW2 Connection Logger discovery log location (user's Clash Verge directory)
DEFAULT_LOG = Path(r"C:\Users\Sanve\OneDrive\Documents\Clash Verge profile update\discovered_ow2_ips.txt")


def parse_log(log_path: Path) -> list[dict]:
    """
    Parse discovered_ow2_ips.txt log file.
    Format: IP,TIMESTAMP,OW2_GROUP,GCP_SCOPE,COUNTRY,ISP
    """
    entries = []
    if not log_path.exists():
        return entries
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(",")
            if len(parts) >= 3:
                ip = parts[0].strip()
                region = parts[2].strip()
                # Convert to CIDR notation
                cidr = f"{ip}/32"
                entries.append({
                    "ip": ip,
                    "cidr": cidr,
                    "region": region,
                    "source": "community",
                })
    return entries


def load_json(json_path: Path) -> dict:
    """Load existing ow2-servers.json."""
    if json_path.exists():
        with open(json_path, encoding="utf-8") as f:
            return json.load(f)
    return {"meta": {}, "regions": {}, "community_discovered": {}}


def save_json(json_path: Path, data: dict):
    """Save JSON."""
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def merge_ips(data: dict, new_entries: list[dict], dry_run: bool = False) -> dict:
    """
    Merge new IPs into the JSON data structure.
    Returns summary of changes.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    summary = {"added": 0, "skipped": 0, "regions": {}}

    existing_cidrs = {}
    for region, rdata in data.get("regions", {}).items():
        existing_cidrs[region] = set(rdata.get("cidrs", []))

    # Collect all discovered from log
    discovered = {}
    for entry in new_entries:
        cidr = entry["cidr"]
        region = entry["region"]
        discovered.setdefault(region, []).append(cidr)

    for region, cidrs in discovered.items():
        if region not in data.get("regions", {}):
            data.setdefault("regions", {})[region] = {
                "description": region.replace("OW2-", "").replace("-", " "),
                "source": "community",
                "last_fetched": now,
                "cidrs": [],
            }
        if region not in existing_cidrs:
            existing_cidrs[region] = set()

        added = []
        skipped = []
        for cidr in cidrs:
            if cidr in existing_cidrs[region]:
                skipped.append(cidr)
            else:
                added.append(cidr)
                existing_cidrs[region].add(cidr)
                data["regions"][region]["cidrs"].append(cidr)

        if added:
            data["regions"][region]["source"] = (
                "foryVERX+community"
                if data["regions"][region].get("source") == "foryVERX"
                else "community"
            )
            data["regions"][region]["last_fetched"] = now
            summary["added"] += len(added)
            summary["skipped"] += len(skipped)
            summary["regions"][region] = {"added": len(added), "skipped": len(skipped), "cidrs": added}

    # Update community_discovered section
    all_discovered = data.get("community_discovered", {}).get("discovered", [])
    existing_discovered = {d["cidr"] for d in all_discovered}

    for entry in new_entries:
        if entry["cidr"] not in existing_discovered:
            all_discovered.append({
                "ip": entry["ip"],
                "cidr": entry["cidr"],
                "region": entry["region"],
                "source": "community",
                "added_at": now,
            })
            existing_discovered.add(entry["cidr"])

    data["community_discovered"] = {
        "description": "IPs discovered via live OW2 game traffic capture (AS57976 Blizzard infrastructure)",
        "last_updated": now,
        "discovered_count": len(all_discovered),
        "discovered": all_discovered,
    }

    # Update meta
    data["meta"] = {
        "version": data.get("meta", {}).get("version", "1.0.0"),
        "last_updated": now,
        "description": data["meta"].get("description", "Overwatch 2 game server IP ranges by region"),
        "source": "foryVERX/Overwatch-Server-Selector + community contributions",
        "format_version": "1.0",
        "total_regions": len(data.get("regions", {})),
        "total_cidrs": sum(len(r.get("cidrs", [])) for r in data.get("regions", {}).values()),
    }

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Merge discovered OW2 IPs into ow2-servers.json"
    )
    parser.add_argument(
        "log_path",
        nargs="?",
        type=Path,
        default=DEFAULT_LOG,
        help="Path to discovered_ow2_ips.txt log file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be added without modifying file",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List IPs in the log file without merging",
    )
    parser.add_argument(
        "--ip",
        help="Manually add a single IP (e.g. 137.221.80.99)",
    )
    parser.add_argument(
        "--region",
        help="Region for manually added IP (e.g. OW2-EU)",
    )
    parser.add_argument(
        "--json",
        default=None,
        help="Path to ow2-servers.json (default: script directory)",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).parent.resolve()
    json_path = Path(args.json) if args.json else (script_dir / "ow2-servers.json")

    print(f"OW2 Server List — Merge Discovered IPs")
    print(f"=" * 50)
    print(f"JSON: {json_path}")
    print()

    # Manual IP add
    if args.ip and args.region:
        data = load_json(json_path)
        cidr = f"{args.ip}/32"
        try:
            ipaddress.ip_address(args.ip)
        except ValueError:
            print(f"[ERROR] Invalid IP address: {args.ip}")
            return
        entry = {"ip": args.ip, "cidr": cidr, "region": args.region}
        summary = merge_ips(data, [entry], dry_run=args.dry_run)
        print(f"[{'DRY RUN: ' if args.dry_run else ''}ADD] {cidr} -> {args.region}")
        if not args.dry_run:
            save_json(json_path, data)
            print(f"Saved to {json_path}")
        return

    # List mode
    if args.list:
        entries = parse_log(args.log_path)
        if not entries:
            print(f"No entries found in {args.log_path}")
            return
        print(f"Found {len(entries)} entries:")
        by_region = {}
        for e in entries:
            by_region.setdefault(e["region"], []).append(e["cidr"])
        for region, cidrs in sorted(by_region.items()):
            print(f"  {region}: {len(cidrs)} IPs")
            for c in sorted(cidrs):
                print(f"    - {c}")
        return

    # Normal merge
    entries = parse_log(args.log_path)
    if not entries:
        print(f"No entries in {args.log_path}")
        print(f"(Run OW2 Connection Logger first to capture IPs)")
        return

    print(f"Parsed {len(entries)} IPs from log:")
    by_region = {}
    for e in entries:
        by_region.setdefault(e["region"], []).append(e["cidr"])
    for region, cidrs in sorted(by_region.items()):
        print(f"  {region}: {len(cidrs)} IPs")

    print()
    data = load_json(json_path)
    summary = merge_ips(data, entries, dry_run=args.dry_run)

    if summary["added"] == 0:
        print("No new IPs to add — all already present.")
        return

    print(f"Changes: +{summary['added']} added, {summary['skipped']} skipped")
    for region, info in sorted(summary["regions"].items()):
        print(f"  {region}: +{info['added']} new")
        for c in info["cidrs"][:3]:
            print(f"    + {c}")
        if len(info["cidrs"]) > 3:
            print(f"    ... and {len(info['cidrs'])-3} more")

    if not args.dry_run:
        save_json(json_path, data)
        print(f"\nSaved to {json_path}")
    else:
        print("\n[DRY RUN] No changes written.")


if __name__ == "__main__":
    main()
