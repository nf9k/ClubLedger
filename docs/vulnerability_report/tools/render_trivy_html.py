#!/usr/bin/env python3
# tools/render_trivy_html.py
#
# Render a clean HTML report from Trivy JSON.
#
# Usage:
#   python3 tools/render_trivy_html.py <image> <trivy.json> <out.html> [allowlist_csv]
#
# Example:
#   python3 tools/render_trivy_html.py myimg:tag reports/trivy.json reports/trivy.html LOW,MEDIUM,HIGH,CRITICAL

import json
import sys
from collections import Counter
from datetime import datetime
from html import escape

HTML_TEMPLATE = """<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Trivy Vulnerability Report</title>
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
    .unknown {{ background: #eaeaea; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 10px; }}
    th, td {{ border: 1px solid #ddd; padding: 6px 8px; vertical-align: top; }}
    th {{ background: #f4f4f4; text-align: left; }}
    tr:nth-child(even) td {{ background: #fafafa; }}
    .sev-critical td.sev {{ background: #ffd6d6; }}
    .sev-high td.sev {{ background: #ffe3c4; }}
    .sev-medium td.sev {{ background: #fff2c2; }}
    .sev-low td.sev {{ background: #d9ecff; }}
    .sev-unknown td.sev {{ background: #eaeaea; }}
    .nowrap {{ white-space: nowrap; }}
    .muted {{ color: #666; }}
    .small {{ font-size: 11px; color: #666; margin-top: 6px; }}
    .foot {{ margin-top: 14px; font-size: 11px; color: #666; }}
    code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }}
  </style>
</head>
<body>
  <h1>Vulnerability Report (Trivy)</h1>
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
    <span class="pill unknown">Unknown: {unknown}</span>
    <span class="muted">Total (shown): {total}</span>
  </div>

  <div class="small">Sorted by severity, then Vulnerability ID, then package.</div>

  <table>
    <thead>
      <tr>
        <th>Severity</th>
        <th>Vuln ID</th>
        <th>Package</th>
        <th>Installed</th>
        <th>Fixed</th>
        <th>Target</th>
        <th>Type</th>
        <th>Title</th>
      </tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>

  <div class="foot">
    Tip: Gate in CI with <code>TRIVY_FAIL_ON=HIGH</code> (or similar) in the Makefile.
  </div>
</body>
</html>
"""

SEV_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4}

def sev_class(sev: str) -> str:
    sev = (sev or "UNKNOWN").upper()
    return {
        "CRITICAL": "sev-critical",
        "HIGH": "sev-high",
        "MEDIUM": "sev-medium",
        "LOW": "sev-low",
        "UNKNOWN": "sev-unknown",
    }.get(sev, "sev-unknown")

def normalize_allowlist(arg: str | None) -> set[str]:
    # Default: show LOW+ (exclude UNKNOWN)
    if not arg:
        return {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    parts = [p.strip().upper() for p in arg.split(",") if p.strip()]
    return set(parts)

def safe(s: str) -> str:
    return escape(s or "")

def main():
    if len(sys.argv) not in (4, 5):
        print("Usage: render_trivy_html.py <image> <trivy.json> <out.html> [allowlist_csv]", file=sys.stderr)
        sys.exit(2)

    image, json_path, out_html = sys.argv[1], sys.argv[2], sys.argv[3]
    allowlist = normalize_allowlist(sys.argv[4] if len(sys.argv) == 5 else None)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Trivy JSON: { Results: [ { Target, Type, Vulnerabilities: [...] }, ... ] }
    results = data.get("Results") or []
    rows = []
    counts = Counter()

    for r in results:
        target = r.get("Target") or ""
        rtype = r.get("Type") or ""
        vulns = r.get("Vulnerabilities") or []
        if not isinstance(vulns, list):
            continue

        for v in vulns:
            sev = (v.get("Severity") or "UNKNOWN").upper()
            if sev not in allowlist:
                continue

            vuln_id = v.get("VulnerabilityID") or ""
            pkg = v.get("PkgName") or ""
            installed = v.get("InstalledVersion") or ""
            fixed = v.get("FixedVersion") or ""
            title = v.get("Title") or ""

            counts[sev] += 1
            rows.append((sev, vuln_id, pkg, installed, fixed, target, rtype, title))

    rows.sort(key=lambda x: (SEV_ORDER.get(x[0], 99), x[1], x[2]))

    rows_html = []
    for sev, vuln_id, pkg, installed, fixed, target, rtype, title in rows:
        rows_html.append(
            f"<tr class='{sev_class(sev)}'>"
            f"<td class='sev nowrap'><b>{safe(sev.title())}</b></td>"
            f"<td class='nowrap'>{safe(vuln_id)}</td>"
            f"<td>{safe(pkg)}</td>"
            f"<td class='nowrap'>{safe(installed)}</td>"
            f"<td>{safe(fixed) if fixed else '<span class=\"muted\">—</span>'}</td>"
            f"<td>{safe(target)}</td>"
            f"<td class='nowrap'>{safe(rtype)}</td>"
            f"<td>{safe(title) if title else '<span class=\"muted\">—</span>'}</td>"
            f"</tr>"
        )

    included_str = ", ".join([s for s in ["LOW", "MEDIUM", "HIGH", "CRITICAL", "UNKNOWN"] if s in allowlist]) or "None"
    total = sum(counts.values())

    html = HTML_TEMPLATE.format(
        image=safe(image),
        generated=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ"),
        included=safe(included_str),
        critical=counts.get("CRITICAL", 0),
        high=counts.get("HIGH", 0),
        medium=counts.get("MEDIUM", 0),
        low=counts.get("LOW", 0),
        unknown=counts.get("UNKNOWN", 0),
        total=total,
        rows="\n".join(rows_html) if rows_html else "<tr><td colspan='8'><i>No matches (for selected severities).</i></td></tr>",
    )

    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Wrote {out_html}")

if __name__ == "__main__":
    main()

