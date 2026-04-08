#!/usr/bin/env python3
# tools/render_grype_html.py
#
# Render a clean HTML report from Grype JSON.
#
# Usage:
#   python3 tools/render_grype_html.py <image> <grype.json> <out.html> [allowlist_csv]
#
# Example:
#   python3 tools/render_grype_html.py myimg:tag reports/grype.json reports/grype.html Low,Medium,High,Critical

import json
import sys
from collections import Counter
from datetime import datetime

HTML_TEMPLATE = """<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Grype Vulnerability Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; }}
    h1 {{ margin: 0 0 6px 0; }}
    .meta {{ color: #555; margin-bottom: 16px; }}
    .summary {{ margin: 16px 0 20px 0; }}
    .pill {{ display: inline-block; padding: 4px 10px; border-radius: 999px; margin-right: 8px; font-size: 12px; }}
    .critical {{ background: #ffd6d6; }}
    .high {{ background: #ffe3c4; }}
    .medium {{ background: #fff2c2; }}
    .low {{ background: #d9ecff; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 10px; }}
    th, td {{ border: 1px solid #ddd; padding: 6px 8px; vertical-align: top; }}
    th {{ background: #f4f4f4; text-align: left; }}
    tr:nth-child(even) td {{ background: #fafafa; }}
    .sev-critical td.sev {{ background: #ffd6d6; }}
    .sev-high td.sev {{ background: #ffe3c4; }}
    .sev-medium td.sev {{ background: #fff2c2; }}
    .sev-low td.sev {{ background: #d9ecff; }}
    .nowrap {{ white-space: nowrap; }}
    .muted {{ color: #666; }}
    .small {{ font-size: 11px; color: #666; margin-top: 6px; }}
    .foot {{ margin-top: 14px; font-size: 11px; color: #666; }}
    code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }}
  </style>
</head>
<body>
  <h1>Vulnerability Report (Grype)</h1>
  <div class="meta">
    Image: <span class="nowrap">{image}</span><br/>
    Generated (UTC): {generated}<br/>
    Included severities: {included}
  </div>

  <div class="summary">
    <span class="pill critical">Critical: {critical}</span>
    <span class="pill high">High: {high}</span>
    <span class="pill medium">Medium: {medium}</span>
    <span class="pill low">Low: {low}</span>
    <span class="muted">Total (shown): {total}</span>
  </div>

  <div class="small">Sorted by severity, then vulnerability ID, then package.</div>

  <table>
    <thead>
      <tr>
        <th>Severity</th>
        <th>Vuln ID</th>
        <th>Package</th>
        <th>Installed</th>
        <th>Fix</th>
        <th>Type</th>
        <th>Location</th>
      </tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>

  <div class="foot">
    Tip: Gate in CI with <code>GRYPE_FAIL_ON=high</code> (or similar) in the Makefile.
  </div>
</body>
</html>
"""

SEV_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Negligible": 4, "Unknown": 5}

def sev_class(s: str) -> str:
    return {
        "Critical": "sev-critical",
        "High": "sev-high",
        "Medium": "sev-medium",
        "Low": "sev-low",
    }.get(s, "")

def normalize_allowlist(arg: str | None) -> set[str]:
    # Default: show Low+ (exclude Negligible/Unknown)
    if not arg:
        return {"Low", "Medium", "High", "Critical"}
    parts = [p.strip() for p in arg.split(",") if p.strip()]
    norm: set[str] = set()
    for p in parts:
        p_lower = p.lower()
        if p_lower == "critical":
            norm.add("Critical")
        elif p_lower == "high":
            norm.add("High")
        elif p_lower == "medium":
            norm.add("Medium")
        elif p_lower == "low":
            norm.add("Low")
        elif p_lower == "negligible":
            norm.add("Negligible")
        elif p_lower == "unknown":
            norm.add("Unknown")
        else:
            # best-effort titlecase
            norm.add(p[:1].upper() + p[1:].lower())
    return norm

def main():
    if len(sys.argv) not in (4, 5):
        print("Usage: render_grype_html.py <image> <grype.json> <out.html> [allowlist_csv]", file=sys.stderr)
        sys.exit(2)

    image, json_path, out_html = sys.argv[1], sys.argv[2], sys.argv[3]
    allowlist = normalize_allowlist(sys.argv[4] if len(sys.argv) == 5 else None)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    all_matches = data.get("matches", []) or []
    matches = []
    for m in all_matches:
        v = m.get("vulnerability") or {}
        sev = v.get("severity") or "Unknown"
        if sev in allowlist:
            matches.append(m)

    sev_counts = Counter()
    rows_data = []

    for m in matches:
        v = m.get("vulnerability") or {}
        a = m.get("artifact") or {}

        sev = v.get("severity", "Unknown") or "Unknown"
        vuln_id = v.get("id", "") or ""
        pkg = a.get("name", "") or ""
        inst = a.get("version", "") or ""
        pkg_type = a.get("type", "") or ""

        fix_versions = (v.get("fix") or {}).get("versions") or []
        fix_str = ", ".join(fix_versions) if fix_versions else ""

        # First location path if present
        locs = a.get("locations") or []
        location = ""
        if isinstance(locs, list) and locs:
            first = locs[0]
            if isinstance(first, dict):
                location = first.get("path") or ""

        sev_counts[sev] += 1
        rows_data.append((sev, vuln_id, pkg, inst, fix_str, pkg_type, location))

    rows_data.sort(key=lambda r: (SEV_ORDER.get(r[0], 99), r[1], r[2]))

    rows_html = []
    for sev, vuln_id, pkg, inst, fix_str, pkg_type, location in rows_data:
        rows_html.append(
            f"<tr class='{sev_class(sev)}'>"
            f"<td class='sev nowrap'><b>{sev}</b></td>"
            f"<td class='nowrap'>{vuln_id}</td>"
            f"<td>{pkg}</td>"
            f"<td class='nowrap'>{inst}</td>"
            f"<td>{fix_str or '<span class=\"muted\">—</span>'}</td>"
            f"<td class='nowrap'>{pkg_type}</td>"
            f"<td>{location or '<span class=\"muted\">—</span>'}</td>"
            f"</tr>"
        )

    total_shown = sum(sev_counts.get(k, 0) for k in ["Critical", "High", "Medium", "Low"])
    included_str = ", ".join([s for s in ["Low", "Medium", "High", "Critical", "Negligible", "Unknown"] if s in allowlist]) or "None"

    html = HTML_TEMPLATE.format(
        image=image,
        generated=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ"),
        included=included_str,
        critical=sev_counts.get("Critical", 0),
        high=sev_counts.get("High", 0),
        medium=sev_counts.get("Medium", 0),
        low=sev_counts.get("Low", 0),
        total=total_shown,
        rows="\n".join(rows_html) if rows_html else "<tr><td colspan='7'><i>No matches (for selected severities).</i></td></tr>",
    )

    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Wrote {out_html}")

if __name__ == "__main__":
    main()

