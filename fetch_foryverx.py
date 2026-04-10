#!/usr/bin/env python3
"""
fetch_foryverx.py — Fetch latest OW2 server IPs from foryVERX/Overwatch-Server-Selector
========================================================================================

Fetches IP CIDR lists from the maintained foryVERX GitHub repo and updates
the local ow2-servers.json with fresh data. Community-discovered IPs are preserved.

Usage:
    python fetch_foryverx.py              # Fetch all regions
    python fetch_foryverx.py OW2-EU      # Fetch specific region only
    python fetch_foryverx.py --dry-run   # Show what would change without modifying file

Output: Updated ow2-servers.json (in same directory as script)
"""

import json
import urllib.request
import ssl
import argparse
from datetime import datetime, timezone
from pathlib import Path

# Region mapping: OW2 name -> foryVERX filename suffix
REGION_MAP = {
    "OW2-NA-East": "NA_East",
    "OW2-NA-Central": "NA_central",
    "OW2-NA-West": "NA_West",
    "OW2-EU": "EU",
    "OW2-Brazil": "Brazil",
    "OW2-Singapore": "AS_Singapore",
    "OW2-Japan": "AS_Japan",
    "OW2-Korea": "AS_Korea",
    "OW2-Taiwan": "AS_Taiwan",
    "OW2-Australia": "Australia",
    "OW2-MiddleEast": "ME",
}

GITHUB_RAW = "https://raw.githubusercontent.com/foryVERX/Overwatch-Server-Selector/main/ip_lists"


def fetch_region(region_name: str, repo_suffix: str) -> list[str]:
    """Fetch CIDR list for one region from foryVERX repo."""
    url = f"{GITHUB_RAW}/Ip_ranges_{repo_suffix}.txt"
    try:
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(url, timeout=15, context=ctx) as r:
            content = r.read().decode("utf-8")
        cidrs = []
        for line in content.replace("\r", "").split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                cidrs.append(line)
        return list(dict.fromkeys(cidrs))  # Deduplicate, preserve order
    except Exception as e:
        print(f"  [WARN] Failed to fetch {region_name}: {e}")
        return []


def load_json(json_path: Path) -> dict:
    """Load existing JSON, or return empty structure if none exists."""
    if json_path.exists():
        with open(json_path, encoding="utf-8") as f:
            return json.load(f)
    return {"meta": {}, "regions": {}, "community_discovered": {}}


def save_json(json_path: Path, data: dict):
    """Save JSON with pretty formatting."""
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch latest OW2 server IPs from foryVERX repo"
    )
    parser.add_argument(
        "regions",
        nargs="*",
        default=[],
        help="Specific regions to update (e.g. OW2-EU OW2-Brazil). "
        "If none, updates all regions.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show changes without modifying the file",
    )
    parser.add_argument(
        "--json",
        default=None,
        help="Path to ow2-servers.json (default: script directory)",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).parent.resolve()
    json_path = Path(args.json) if args.json else (script_dir / "ow2-servers.json")

    data = load_json(json_path)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Determine which regions to update
    regions_to_update = []
    if args.regions:
        for r in args.regions:
            if r in REGION_MAP:
                regions_to_update.append(r)
            else:
                print(f"[WARN] Unknown region: {r}")
        if not regions_to_update:
            print("[ERROR] No valid regions specified")
            return
    else:
        regions_to_update = list(REGION_MAP.keys())

    print(f"Fetching OW2 server IPs from foryVERX...")
    print(f"Target: {json_path}")
    print(f"Regions: {', '.join(regions_to_update)}")
    print()

    total_new = 0
    total_removed = 0

    for region_name in regions_to_update:
        repo_suffix = REGION_MAP[region_name]
        old_cidrs = list(data.get("regions", {}).get(region_name, {}).get("cidrs", []))
        old_cidrs_set = set(old_cidrs)

        new_cidrs = fetch_region(region_name, repo_suffix)
        new_cidrs_set = set(new_cidrs)

        # Community IPs are /32s that are NOT in the foryVERX data
        # Preserve them: add any old /32s that aren't in new data
        preserved = []
        for c in old_cidrs:
            if c.endswith("/32") and c not in new_cidrs_set:
                preserved.append(c)  # Keep community /32 IPs

        # Merge: foryVERX data + preserved community IPs
        merged = list(dict.fromkeys(new_cidrs + preserved))  # Dedupe, foryVERX first

        added = set(merged) - old_cidrs_set
        removed_from_foryverx = old_cidrs_set - new_cidrs_set - set(preserved)

        if added or removed_from_foryverx:
            print(f"  {region_name}:")
            if added:
                print(f"    + {len(added)} new CIDRs")
                for c in sorted(added)[:5]:
                    print(f"      + {c}")
                if len(added) > 5:
                    print(f"      ... and {len(added)-5} more")
            if removed_from_foryverx:
                print(f"    - {len(removed_from_foryverx)} removed (from foryVERX)")
        else:
            print(f"  {region_name}: no changes")

        total_new += len(added)
        total_removed += len(removed_from_foryverx)

        # Determine source
        source = "foryVERX"
        if preserved:
            source = "foryVERX+community"

        # Update data structure
        if region_name not in data.get("regions", {}):
            data.setdefault("regions", {})[region_name] = {}
        data["regions"][region_name] = {
            "description": region_name.replace("OW2-", "").replace("-", " "),
            "source": source,
            "last_fetched": now,
            "cidrs": merged,
        }

    # Update meta
    data["meta"] = {
        "version": data.get("meta", {}).get("version", "1.0.0"),
        "last_updated": now,
        "description": "Overwatch 2 game server IP ranges by region",
        "source": "foryVERX/Overwatch-Server-Selector + community contributions",
        "format_version": "1.0",
        "total_regions": len(data.get("regions", {})),
        "total_cidrs": sum(len(r.get("cidrs", [])) for r in data.get("regions", {}).values()),
    }

    print()
    print(f"Summary: +{total_new} added, -{total_removed} removed")

    if not args.dry_run:
        save_json(json_path, data)
        print(f"Saved to {json_path}")
    else:
        print("[DRY RUN] No changes written.")


if __name__ == "__main__":
    main()
