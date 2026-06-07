# FamilyHostsBlocker

GitHub-only phase for generating a Windows `hosts`-compatible adult/NSFW domain blocklist.

This repository does **not** modify any Windows `hosts` file. It only builds and publishes generated blocklist files.

## Flow

```text
External adult/NSFW sources
-> GitHub Actions
-> scripts/update_hosts.py
-> familyblocker_domains.txt
-> familyblocker_hosts.txt
-> familyblocker_sources_report.tsv
```

## Repository structure

```text
FamilyHostsBlocker/
├─ domains_manual.txt
├─ domains_auto.txt
├─ domains_allowlist.txt
├─ sources_enabled.txt
├─ sources_disabled.txt
├─ familyblocker_domains.txt
├─ familyblocker_hosts.txt
├─ familyblocker_sources_report.tsv
├─ scripts/
│  └─ update_hosts.py
└─ .github/
   └─ workflows/
      └─ update_hosts.yml
```

## Enabled sources

- StevenBlack hosts, porn extension
- Block List Project, porn list
- OISD NSFW
- HaGeZi NSFW

Edit `sources_enabled.txt` to enable or disable sources.

## Manual additions

Add manual domains to:

```text
domains_manual.txt
```

Use one domain per line.

## Allowlist

Add domains that must not be blocked to:

```text
domains_allowlist.txt
```

Supported forms:

```text
example.com
*.example.com
.example.com
```

## Generated outputs

- `domains_auto.txt`: cleaned domains from external sources only.
- `familyblocker_domains.txt`: final domains after manual additions and allowlist.
- `familyblocker_hosts.txt`: final Windows hosts-compatible entries.
- `familyblocker_sources_report.tsv`: source traceability report.

## Public raw URLs

Domains only:

```text
https://raw.githubusercontent.com/italesawy-droid/FamilyHostsBlocker/main/familyblocker_domains.txt
```

Hosts format:

```text
https://raw.githubusercontent.com/italesawy-droid/FamilyHostsBlocker/main/familyblocker_hosts.txt
```

## Manual run

From the repository root:

```bash
python scripts/update_hosts.py
```

## GitHub Actions

The workflow runs:

- manually with `workflow_dispatch`
- daily by schedule
- after edits to source, allowlist, manual-domain, or builder files

The workflow commits the generated files back to the repository.

## Important limitation

This phase only generates lists on GitHub. A separate Windows phase will later download `familyblocker_hosts.txt` and apply it safely inside a managed block in the local `hosts` file.
