# OW2 Server List

> Community-maintained Overwatch 2 game server IP ranges organized by region.

This repo contains a single `ow2-servers.json` file with all known OW2 server IP CIDRs, pulled from the maintained [foryVERX/Overwatch-Server-Selector](https://github.com/foryVERX/Overwatch-Server-Selector) repo plus community-discovered IPs.

## Quick Start

### For Clash Verge / Clash.Meta Users

1. Download the latest `ow2-servers.json`
2. Run the profile generator:

```bash
# Fetch latest from foryVERX
python fetch_foryverx.py

# Merge any community discoveries
python merge_discovered.py

# Generate Clash YAML profile
python generate_profile.py --auth-direct
```

3. Import `ow2-profile.yaml` into Clash Verge

### For Contributors

If you discover new OW2 server IPs (e.g., via the OW2 Connection Logger), contribute them here:

```bash
# After capturing IPs with the OW2 Connection Logger,
# copy discovered_ow2_ips.txt to the repo
cp ~/discovered_ow2_ips.txt .

# Merge into the JSON
python merge_discovered.py discovered_ow2_ips.txt

# Commit and submit a PR
git add ow2-servers.json
git commit -m "chore: add X new IPs discovered via live capture"
```

## File Format

`ow2-servers.json` structure:

```json
{
  "meta": {
    "version": "1.0.0",
    "last_updated": "2026-04-10T18:00:00Z",
    "total_regions": 11,
    "total_cidrs": 571,
    "source": "foryVERX/Overwatch-Server-Selector + community contributions"
  },
  "regions": {
    "OW2-EU": {
      "description": "EU",
      "source": "foryVERX+community",
      "last_fetched": "2026-04-10T18:00:00Z",
      "cidrs": [
        "64.224.26.0/23",
        "104.155.0.0/17",
        "137.221.78.99/32",
        ...
      ]
    },
    ...
  },
  "community_discovered": {
    "description": "IPs discovered via live OW2 game traffic capture",
    "discovered_count": 7,
    "discovered": [
      {"ip": "137.221.80.99", "cidr": "137.221.80.99/32", "region": "OW2-EU"},
      ...
    ]
  }
}
```

## Scripts

### `fetch_foryverx.py`

Fetches the latest IP lists from the foryVERX GitHub repo.

```bash
# Update all regions
python fetch_foryverx.py

# Update specific regions
python fetch_foryverx.py OW2-EU OW2-Brazil

# Preview changes without writing
python fetch_foryverx.py --dry-run
```

### `merge_discovered.py`

Merges IPs from the OW2 Connection Logger's `discovered_ow2_ips.txt` into the JSON.

```bash
# Use default log location
python merge_discovered.py

# Use custom log file
python merge_discovered.py path/to/discovered_ow2_ips.txt

# List IPs without merging
python merge_discovered.py --list

# Add a single IP manually
python merge_discovered.py --ip 137.221.80.99 --region OW2-EU

# Preview without writing
python merge_discovered.py --dry-run
```

### `generate_profile.py`

Generates a ready-to-use Clash Verge YAML profile from the JSON.

```bash
# Generate profile.yaml in current directory
python generate_profile.py

# Custom output path
python generate_profile.py -o my_ow2_profile.yaml

# Include Battle.net auth -> DIRECT (recommended for server switching)
python generate_profile.py --auth-direct
```

## Regions

| Region | Description | Proxy Group |
|--------|-------------|------------|
| `OW2-NA-East` | Virginia / IAD1 | OW2-NA-East |
| `OW2-NA-Central` | Texas / ORD1 | OW2-NA-Central |
| `OW2-NA-West` | Los Angeles / LAX1 | OW2-NA-West |
| `OW2-EU` | Europe (AMS1, FRA1, GEN1) | OW2-EU |
| `OW2-Brazil` | Sao Paulo / GBR1 | OW2-Brazil |
| `OW2-Singapore` | Singapore / GSG1 | OW2-Singapore |
| `OW2-Japan` | Tokyo | OW2-Japan |
| `OW2-Korea` | Seoul / ICN1 | OW2-Korea |
| `OW2-Taiwan` | Taipei / TPE1 | OW2-Taiwan |
| `OW2-Australia` | Sydney / SYD2 | OW2-Australia |
| `OW2-MiddleEast` | Bahrain / MES1, GMEC2 | OW2-MiddleEast |

## Community Discovery

The `community_discovered` section contains IPs found via live OW2 game traffic capture. These are AS57976 (Blizzard Entertainment) IPs that aren't in the GCP/AWS ranges covered by foryVERX.

If you capture new IPs using the [OW2 Connection Logger](https://github.com/Qiiks/ow2-server-list), merge them here so others benefit.

## Data Sources

- **foryVERX/Overwatch-Server-Selector** — Maintained IP lists updated periodically
- **Community contributions** — Live-captured IPs from actual OW2 game traffic
- **GCP cloud.json** — Used for GCP-hosted OW2 server geo-mapping

## License

MIT — contribute freely.
