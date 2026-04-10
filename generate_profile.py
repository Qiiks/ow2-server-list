#!/usr/bin/env python3
"""
generate_profile.py — Generate Clash Verge YAML profile from ow2-servers.json
==========================================================================

Generates a ready-to-use Clash Verge YAML profile from the ow2-servers.json
data file. Supports customization of proxy group names and auth rules.

Usage:
    python generate_profile.py                                    # Generate profile.yaml
    python generate_profile.py --output my_profile.yaml            # Custom output path
    python generate_profile.py --include-process-name             # Add PROCESS-NAME rules
    python generate_profile.py --auth-direct                        # Battle.net -> DIRECT
    python generate_profile.py --all-regions                       # Include all regions

Output: Clash Verge YAML profile (.yaml file)
"""

import json
import argparse
import re
import ipaddress
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_JSON = Path(__file__).parent / "ow2-servers.json"

# Clash Verge proxy group names used in the profile
PROXY_GROUPS = [
    "Game-Mode",
    "OW2-NA-Central",
    "OW2-NA-East",
    "OW2-NA-West",
    "OW2-EU",
    "OW2-Singapore",
    "OW2-Japan",
    "OW2-Korea",
    "OW2-Taiwan",
    "OW2-Australia",
    "OW2-Brazil",
    "OW2-MiddleEast",
]

# Default Clash Verge proxies to include (minimal set)
DEFAULT_PROXIES = [
    {"name": "Hysteria-Home", "type": "hysteria2", "server": "127.0.0.1", "port": 443},
]


def load_json(json_path: Path) -> dict:
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


def ip_overlaps_cidrs(ip_str: str, cidr_list: list[str]) -> bool:
    """Check if an IP is covered by any CIDR in the list."""
    try:
        ip = ipaddress.ip_address(ip_str)
        for cidr in cidr_list:
            if ip in ipaddress.ip_network(cidr, strict=False):
                return True
        return False
    except ValueError:
        return False


def generate_auth_rules() -> list[str]:
    """Generate auth/launcher DIRECT rules."""
    return [
        "# -- Blizzard launcher/auth ------------------------------------------",
        "# Auth servers must go DIRECT — keeps Battle.net session stable",
        "# when switching game server regions mid-session.",
        "# Game server IPs (from foryVERX repo) are SEPARATE from auth servers.",
        "- DOMAIN-SUFFIX,battle.net,DIRECT",
        "- DOMAIN-SUFFIX,battlenet.com,DIRECT",
        "- IP-CIDR,137.221.106.0/24,DIRECT,no-resolve",
        "- IP-CIDR,166.117.0.0/16,DIRECT,no-resolve",
    ]


def generate_game_rules(data: dict, include_cidr: str | None = None) -> list[str]:
    """Generate IP-CIDR rules for game servers."""
    rules = []
    rules.append("")
    rules.append("# -- Game traffic (UDP) -> proxy through region group --")
    rules.append("# Route ONLY known game server IPs through region proxies.")
    rules.append("# This allows server switching without breaking auth session.")

    region_order = [
        "OW2-NA-East", "OW2-NA-Central", "OW2-NA-West",
        "OW2-EU",
        "OW2-Singapore", "OW2-Japan", "OW2-Korea", "OW2-Taiwan",
        "OW2-Australia", "OW2-Brazil",
        "OW2-MiddleEast",
    ]

    regions = data.get("regions", {})

    for region in region_order:
        if region not in regions:
            continue
        rdata = regions[region]
        cidrs = rdata.get("cidrs", [])
        if not cidrs:
            continue

        # Optionally filter by CIDR (e.g., "34.0.0.0/8" to include only)
        if include_cidr:
            filtered = [c for c in cidrs if ip_overlaps_cidrs(include_cidr, [include_cidr]) or c == include_cidr]
        else:
            filtered = cidrs

        if not filtered:
            continue

        rules.append("")
        rules.append(f"# -- {region} ({len(filtered)} CIDRs) --")
        for cidr in sorted(filtered):
            rules.append(f"- IP-CIDR,{cidr},{region},no-resolve")

    return rules


def generate_process_rules(args) -> list[str]:
    """Generate PROCESS-NAME rules."""
    rules = []
    rules.append("")
    rules.append("# -- PROCESS-NAME -----------------------------------------------")
    if args.auth_direct:
        rules.append("# Battle.net.exe: force DIRECT (auth bypasses proxy for session stability)")
        rules.append("# Overwatch.exe: go through Game-Mode proxy group")
        rules.append("- PROCESS-NAME,Battle.net.exe,DIRECT")
        rules.append("- PROCESS-NAME,Overwatch.exe,Game-Mode")
    else:
        rules.append("- PROCESS-NAME,Battle.net.exe,Game-Mode")
        rules.append("- PROCESS-NAME,Overwatch.exe,Game-Mode")
    return rules


def generate_default_rules() -> list[str]:
    """Generate DEFAULT/MATCH rule."""
    return [
        "",
        "# -- DEFAULT ---------------------------------------------------",
        "- MATCH,DIRECT",
    ]


def generate_profile(args) -> str:
    """Generate the complete YAML profile content."""
    data = load_json(args.json)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    total_cidrs = sum(len(r.get("cidrs", [])) for r in data.get("regions", {}).values())

    lines = []
    lines.append("# OW2 Clash Verge Profile")
    lines.append(f"# Generated: {now}")
    lines.append(f"# Source: ow2-server-list (foryVERX + community)")
    lines.append(f"# Total IP-CIDR rules: {total_cidrs}")
    lines.append(f"# https://github.com/YOUR_USERNAME/ow2-server-list")
    lines.append("")

    # Proxies
    lines.append("proxies:")
    for proxy in DEFAULT_PROXIES:
        lines.append(f'  - name: "{proxy["name"]}"')
        lines.append(f'    type: {proxy["type"]}')
        lines.append(f'    server: {proxy["server"]}')
        lines.append(f'    port: {proxy["port"]}')
    lines.append("")

    # Proxy groups
    lines.append("proxy-groups:")
    lines.append('  - name: "Game-Mode"')
    lines.append("    type: select")
    lines.append("    proxies:")
    lines.append('      - "DIRECT"')
    for pg in PROXY_GROUPS:
        lines.append(f'      - "{pg}"')

    for pg in PROXY_GROUPS:
        lines.append(f'  - name: "{pg}"')
        lines.append("    type: select")
        lines.append("    proxies:")
        lines.append('      - "Hysteria-Home"')

    # Rules
    lines.extend(generate_auth_rules())
    lines.extend(generate_game_rules(data, include_cidr=args.include_cidr))
    lines.extend(generate_process_rules(args))
    lines.extend(generate_default_rules())

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="Generate Clash Verge YAML profile from ow2-servers.json"
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=DEFAULT_JSON,
        help=f"Path to ow2-servers.json (default: {DEFAULT_JSON})",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("ow2-profile.yaml"),
        help="Output YAML file path",
    )
    parser.add_argument(
        "--auth-direct",
        action="store_true",
        help="Set Battle.net auth to DIRECT (recommended for server switching)",
    )
    parser.add_argument(
        "--all-regions",
        action="store_true",
        help="Include all regions (even empty ones)",
    )
    parser.add_argument(
        "--include-cidr",
        help="Only include CIDRs within this range (e.g. 34.0.0.0/8)",
    )
    args = parser.parse_args()

    json_path = Path(args.json)
    if not json_path.exists():
        print(f"[ERROR] JSON file not found: {json_path}")
        print("Run fetch_foryverx.py first to download the data.")
        return

    print(f"Generating profile from {json_path}...")
    profile = generate_profile(args)

    output_path = args.output
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(profile)

    print(f"Generated: {output_path}")
    print(f"  Lines: {len(profile.splitlines())}")


if __name__ == "__main__":
    main()
