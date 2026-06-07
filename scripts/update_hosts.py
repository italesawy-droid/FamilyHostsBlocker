#!/usr/bin/env python3
"""
FamilyHostsBlocker GitHub list builder.

This script downloads enabled external adult/NSFW domain sources, extracts
domains from common blocklist formats, applies the allowlist, merges manual
domains, and writes:

- domains_auto.txt
- familyblocker_domains.txt
- familyblocker_hosts.txt
- familyblocker_sources_report.tsv

It does not modify any Windows hosts file.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import ipaddress
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple


ROOT = Path(__file__).resolve().parents[1]

SOURCES_ENABLED = ROOT / "sources_enabled.txt"
DOMAINS_MANUAL = ROOT / "domains_manual.txt"
DOMAINS_ALLOWLIST = ROOT / "domains_allowlist.txt"

OUT_AUTO = ROOT / "domains_auto.txt"
OUT_DOMAINS = ROOT / "familyblocker_domains.txt"
OUT_HOSTS = ROOT / "familyblocker_hosts.txt"
OUT_REPORT = ROOT / "familyblocker_sources_report.tsv"

BLOCK_IP = "0.0.0.0"
USER_AGENT = "FamilyHostsBlocker/1.0 GitHubListBuilder"

LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
HOSTS_IPS = {"0.0.0.0", "127.0.0.1", "::1", "255.255.255.255"}

BAD_DOMAINS = {
    "localhost",
    "local",
    "broadcasthost",
    "ip6-localhost",
    "ip6-loopback",
    "ip6-localnet",
    "ip6-mcastprefix",
    "ip6-allnodes",
    "ip6-allrouters",
    "0.0.0.0",
    "127.0.0.1",
    "::1",
}


def read_text_lines(path: Path) -> List[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def strip_inline_comment(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return ""
    if stripped.startswith(("#", "!", ";")):
        return ""

    if "#" in stripped:
        stripped = stripped.split("#", 1)[0].strip()

    return stripped


def normalize_domain(candidate: str) -> Optional[str]:
    if not candidate:
        return None

    candidate = candidate.strip().strip("'\"`").strip()
    candidate = candidate.rstrip(".")
    candidate = candidate.lower()

    if not candidate:
        return None

    candidate = candidate.replace("\\", "/")

    if candidate.startswith("||"):
        candidate = candidate[2:]
    if candidate.startswith("|"):
        candidate = candidate[1:]
    if candidate.startswith("*."):
        candidate = candidate[2:]
    if candidate.startswith("."):
        candidate = candidate[1:]

    for sep in ("^", "$", "/", ","):
        if sep in candidate:
            candidate = candidate.split(sep, 1)[0]

    candidate = candidate.strip().rstrip(".")

    if not candidate or candidate in BAD_DOMAINS:
        return None

    if "://" in candidate:
        parsed = urllib.parse.urlsplit(candidate)
        candidate = parsed.hostname or ""
        candidate = candidate.lower().rstrip(".")

    if candidate.startswith("[") and "]" in candidate:
        return None

    if ":" in candidate and candidate.count(":") == 1:
        host, maybe_port = candidate.rsplit(":", 1)
        if maybe_port.isdigit():
            candidate = host

    if candidate in BAD_DOMAINS:
        return None

    try:
        ipaddress.ip_address(candidate)
        return None
    except ValueError:
        pass

    try:
        candidate = candidate.encode("idna").decode("ascii")
    except UnicodeError:
        return None

    if len(candidate) > 253:
        return None
    if "." not in candidate:
        return None

    labels = candidate.split(".")
    if any(not label for label in labels):
        return None
    if any(not LABEL_RE.match(label) for label in labels):
        return None

    tld = labels[-1]
    if len(tld) < 2:
        return None
    if not (tld.startswith("xn--") or re.match(r"^[a-z]{2,63}$", tld)):
        return None

    return candidate


def extract_domains_from_line(line: str) -> List[str]:
    line = strip_inline_comment(line)
    if not line:
        return []

    dnsmasq = re.match(r"^\s*address=/([^/]+)/", line, re.IGNORECASE)
    if dnsmasq:
        domain = normalize_domain(dnsmasq.group(1))
        return [domain] if domain else []

    if line.startswith("||"):
        domain = normalize_domain(line)
        return [domain] if domain else []

    if "://" in line:
        domain = normalize_domain(line)
        return [domain] if domain else []

    parts = line.split()
    if not parts:
        return []

    first = parts[0].lower()

    if first in HOSTS_IPS:
        domains = []
        for token in parts[1:]:
            domain = normalize_domain(token)
            if domain:
                domains.append(domain)
        return domains

    try:
        ipaddress.ip_address(first)
        domains = []
        for token in parts[1:]:
            domain = normalize_domain(token)
            if domain:
                domains.append(domain)
        return domains
    except ValueError:
        pass

    domain = normalize_domain(parts[0])
    return [domain] if domain else []


def read_sources(path: Path) -> List[str]:
    urls: List[str] = []
    for raw in read_text_lines(path):
        line = strip_inline_comment(raw)
        if not line:
            continue
        if not (line.startswith("http://") or line.startswith("https://")):
            print(f"Skipping non-URL source: {line}", file=sys.stderr)
            continue
        urls.append(line)
    return urls


def fetch_url(url: str, timeout: int) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
    return raw.decode("utf-8", errors="replace")


def add_domains_from_lines(
    lines: Iterable[str],
    source_label: str,
    domain_sources: Dict[str, Set[str]],
) -> Set[str]:
    added: Set[str] = set()
    for line in lines:
        for domain in extract_domains_from_line(line):
            domain_sources.setdefault(domain, set()).add(source_label)
            added.add(domain)
    return added


def read_allowlist(path: Path) -> Tuple[Set[str], Set[str]]:
    exact: Set[str] = set()
    suffix: Set[str] = set()

    for line in read_text_lines(path):
        stripped = strip_inline_comment(line)
        if not stripped:
            continue

        is_suffix = stripped.startswith("*.") or stripped.startswith(".")
        domain = normalize_domain(stripped)
        if not domain:
            continue

        if is_suffix:
            suffix.add(domain)
        else:
            exact.add(domain)

    return exact, suffix


def is_allowed(domain: str, exact: Set[str], suffix: Set[str]) -> bool:
    if domain in exact:
        return True

    for allowed_suffix in suffix:
        if domain == allowed_suffix or domain.endswith("." + allowed_suffix):
            return True

    return False


def write_lines(path: Path, lines: Iterable[str]) -> None:
    text = "\n".join(lines)
    if text:
        text += "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def build(timeout: int, strict: bool) -> int:
    domain_sources: Dict[str, Set[str]] = {}
    source_counts: List[Tuple[str, int]] = []
    failed_sources: List[str] = []

    urls = read_sources(SOURCES_ENABLED)
    if not urls:
        print("No enabled sources found.", file=sys.stderr)
        return 2

    for url in urls:
        try:
            text = fetch_url(url, timeout=timeout)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            message = f"Failed to fetch source: {url} -> {exc}"
            failed_sources.append(message)
            if strict:
                print(message, file=sys.stderr)
                return 2
            print("WARNING: " + message, file=sys.stderr)
            continue

        before = len(domain_sources)
        add_domains_from_lines(text.splitlines(), url, domain_sources)
        after = len(domain_sources)
        source_counts.append((url, after - before))

    auto_before_allowlist = set(domain_sources.keys())

    add_domains_from_lines(
        read_text_lines(DOMAINS_MANUAL),
        "manual:domains_manual.txt",
        domain_sources,
    )

    exact_allow, suffix_allow = read_allowlist(DOMAINS_ALLOWLIST)

    filtered_domains = sorted(
        domain for domain in domain_sources
        if not is_allowed(domain, exact_allow, suffix_allow)
    )

    auto_domains = sorted(
        domain for domain in auto_before_allowlist
        if not is_allowed(domain, exact_allow, suffix_allow)
    )

    if not filtered_domains:
        print("No final domains were produced. Refusing to write empty production lists.", file=sys.stderr)
        return 3

    generated_at = _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    write_lines(
        OUT_AUTO,
        [
            "# Generated by FamilyHostsBlocker.",
            f"# Generated at: {generated_at}",
            "# Source: enabled external sources only.",
            "",
            *auto_domains,
        ],
    )

    write_lines(
        OUT_DOMAINS,
        [
            "# Generated by FamilyHostsBlocker.",
            f"# Generated at: {generated_at}",
            "# Source: external sources + domains_manual.txt, after allowlist.",
            "",
            *filtered_domains,
        ],
    )

    write_lines(
        OUT_HOSTS,
        [
            "# Generated by FamilyHostsBlocker.",
            f"# Generated at: {generated_at}",
            "# Format: Windows hosts-compatible entries.",
            "",
            *[f"{BLOCK_IP} {domain}" for domain in filtered_domains],
        ],
    )

    report_lines = ["domain\tsource_count\tsources"]
    for domain in filtered_domains:
        sources = sorted(domain_sources.get(domain, set()))
        report_lines.append(f"{domain}\t{len(sources)}\t" + " | ".join(sources))
    write_lines(OUT_REPORT, report_lines)

    print(f"Enabled sources: {len(urls)}")
    for url, count in source_counts:
        print(f"Source unique additions: {count}\t{url}")
    if failed_sources:
        print(f"Failed sources: {len(failed_sources)}", file=sys.stderr)
    print(f"Auto domains after allowlist: {len(auto_domains)}")
    print(f"Final domains after manual + allowlist: {len(filtered_domains)}")
    print(f"Wrote: {OUT_DOMAINS.relative_to(ROOT)}")
    print(f"Wrote: {OUT_HOSTS.relative_to(ROOT)}")
    print(f"Wrote: {OUT_REPORT.relative_to(ROOT)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Build FamilyHostsBlocker domain and hosts files.")
    parser.add_argument("--timeout", type=int, default=120, help="HTTP timeout per source in seconds.")
    parser.add_argument("--strict", action="store_true", help="Fail if any source cannot be fetched.")
    args = parser.parse_args()
    return build(timeout=args.timeout, strict=args.strict)


if __name__ == "__main__":
    raise SystemExit(main())
