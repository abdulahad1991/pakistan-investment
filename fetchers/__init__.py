"""Single-responsibility data fetchers for pakinvestlysis.com.

Each module owns ONE data category. It exposes a pure ``parse_*`` function
(no network — unit-tested against captured fixtures in tests/fixtures/) and a
``fetch()`` that does the HTTP call, parses, validates, and returns a
provenance-wrapped *partition* dict. Fetchers write to data/partitions/<name>.json
and NEVER touch data.json directly — build_data.py merges partitions into the
single live data.json the site reads.

Why split: the old monolith fetch_data.py silently froze stale values via a
blanket try/except (inflation was never even fetched). Splitting gives
per-source observability, per-cadence scheduling, isolated outputs (no shared
write race), and — critically — provenance + staleness so wrong/old data is
visible, never silently served as current.
"""
