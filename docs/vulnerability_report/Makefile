# Makefile — Grype + Trivy JSON + nice HTML + PDF (LMDE7 / Debian 12)
#
# Targets:
#   make security-reports IMAGE=repo/app:tag     # run BOTH grype+trivy, produce PDFs
#   make grype-report     IMAGE=repo/app:tag     # grype only
#   make trivy-report     IMAGE=repo/app:tag     # trivy only
#   make deps                                 # install deps (LMDE7)
#   make clean
#
# CI gating:
#   make security-reports IMAGE=... GRYPE_FAIL_ON=high TRIVY_FAIL_ON=HIGH
#
# Outputs (default under ./reports/):
#   - grype-<safe-image>-<timestamp>.json/html/pdf
#   - trivy-<safe-image>-<timestamp>.json/html/pdf
#
# Notes:
# - Uses Chromium headless for HTML->PDF (wkhtmltopdf not in Debian 12/LMDE7 repos).
# - Grype display filtering (e.g., skip Negligible) happens in tools/render_grype_html.py.
# - Trivy display filtering happens in tools/render_trivy_html.py.
# - JSON artifacts are kept for audit/diff.

SHELL := /bin/bash

# ---- User-configurable vars ----
IMAGE ?=
OUTDIR ?= reports

# Display allowlists (affects HTML/PDF only)
# Grype: Critical, High, Medium, Low, Negligible, Unknown
GRYPE_REPORT_SEVERITIES ?= Low,Medium,High,Critical
# Trivy: UNKNOWN, LOW, MEDIUM, HIGH, CRITICAL
TRIVY_REPORT_SEVERITIES ?= LOW,MEDIUM,HIGH,CRITICAL

# CI gating thresholds (optional)
# Grype: none | low | medium | high | critical
GRYPE_FAIL_ON ?= none
# Trivy: NONE | LOW | MEDIUM | HIGH | CRITICAL
TRIVY_FAIL_ON ?= NONE

# Tooling
GRYPE ?= grype
TRIVY ?= trivy
CHROMIUM ?= chromium
PYTHON ?= python3

# Timestamped filenames
TIMESTAMP := $(shell date -u +%Y%m%dT%H%M%SZ)
SAFE_TAG := $(shell echo "$(IMAGE)" | sed 's/[^A-Za-z0-9._-]/_/g')

# Renderers
GRYPE_RENDER := tools/render_grype_html.py
TRIVY_RENDER := tools/render_trivy_html.py

# Artifact names
GRYPE_BASENAME := grype-$(SAFE_TAG)-$(TIMESTAMP)
TRIVY_BASENAME := trivy-$(SAFE_TAG)-$(TIMESTAMP)

GRYPE_JSON := $(OUTDIR)/$(GRYPE_BASENAME).json
GRYPE_HTML := $(OUTDIR)/$(GRYPE_BASENAME).html
GRYPE_PDF  := $(OUTDIR)/$(GRYPE_BASENAME).pdf

TRIVY_JSON := $(OUTDIR)/$(TRIVY_BASENAME).json
TRIVY_HTML := $(OUTDIR)/$(TRIVY_BASENAME).html
TRIVY_PDF  := $(OUTDIR)/$(TRIVY_BASENAME).pdf

.PHONY: help deps check-image security-reports grype-report trivy-report clean

help:
	@echo "Targets:"
	@echo "  make security-reports IMAGE=repo/app:tag   # Grype + Trivy reports (PDFs)"
	@echo "  make grype-report     IMAGE=repo/app:tag   # Grype only"
	@echo "  make trivy-report     IMAGE=repo/app:tag   # Trivy only"
	@echo "  make deps                                   # install deps (LMDE7)"
	@echo "  make clean"
	@echo ""
	@echo "Vars:"
	@echo "  IMAGE=...                  (required)"
	@echo "  OUTDIR=reports             (default: reports)"
	@echo "  GRYPE_REPORT_SEVERITIES=Low,Medium,High,Critical"
	@echo "  TRIVY_REPORT_SEVERITIES=LOW,MEDIUM,HIGH,CRITICAL"
	@echo "  GRYPE_FAIL_ON=none|low|medium|high|critical"
	@echo "  TRIVY_FAIL_ON=NONE|LOW|MEDIUM|HIGH|CRITICAL"

deps:
	sudo apt update
	sudo apt install -y jq python3 chromium curl
	@echo "Installing Trivy..."
	curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sudo sh -s -- -b /usr/local/bin
	@echo "Installing Grype..."
	curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sudo sh -s -- -b /usr/local/bin

check-image:
	@if [[ -z "$(IMAGE)" ]]; then \
		echo "ERROR: IMAGE is required. Example: make security-reports IMAGE=myapp:1.2.3"; \
		exit 2; \
	fi

$(OUTDIR):
	@mkdir -p "$(OUTDIR)"

# -------------------
# Composite target (requested)
# -------------------
security-reports: check-image grype-report trivy-report
	@echo ""
	@echo "==> All reports complete for $(IMAGE)"

# -------------------
# Grype targets
# -------------------
grype-report: check-image $(GRYPE_PDF)
	@echo ""
	@echo "Wrote (Grype):"
	@echo "  $(GRYPE_JSON)"
	@echo "  $(GRYPE_HTML)"
	@echo "  $(GRYPE_PDF)"
	@echo ""
	@if [[ "$(GRYPE_FAIL_ON)" != "none" ]]; then \
		echo "==> Grype CI Gate: failing on $(GRYPE_FAIL_ON)+ severities"; \
		$(GRYPE) "$(IMAGE)" --fail-on "$(GRYPE_FAIL_ON)" >/dev/null; \
		echo "==> Grype gate passed"; \
	fi

$(GRYPE_JSON): | $(OUTDIR)
	@echo "==> Grype scan: $(IMAGE)"
	$(GRYPE) "$(IMAGE)" -o json > "$(GRYPE_JSON)"
	@echo "==> JSON: $(GRYPE_JSON)"

$(GRYPE_HTML): $(GRYPE_JSON)
	@echo "==> Render Grype HTML (display severities: $(GRYPE_REPORT_SEVERITIES))"
	$(PYTHON) "$(GRYPE_RENDER)" "$(IMAGE)" "$(GRYPE_JSON)" "$(GRYPE_HTML)" "$(GRYPE_REPORT_SEVERITIES)"
	@echo "==> HTML: $(GRYPE_HTML)"

$(GRYPE_PDF): $(GRYPE_HTML)
	@echo "==> Render Grype PDF (Chromium headless)"
	$(CHROMIUM) --headless --disable-gpu --no-sandbox \
		--print-to-pdf="$(GRYPE_PDF)" \
		"file://$$(realpath "$(GRYPE_HTML)")" >/dev/null 2>&1 || true
	@if [[ ! -s "$(GRYPE_PDF)" ]]; then \
		echo "ERROR: Grype PDF generation failed. Try running chromium manually:"; \
		echo "  chromium --headless --disable-gpu --no-sandbox --print-to-pdf=$(GRYPE_PDF) file://$$(realpath $(GRYPE_HTML))"; \
		exit 1; \
	fi
	@echo "==> PDF: $(GRYPE_PDF)"

# -------------------
# Trivy targets
# -------------------
trivy-report: check-image $(TRIVY_PDF)
	@echo ""
	@echo "Wrote (Trivy):"
	@echo "  $(TRIVY_JSON)"
	@echo "  $(TRIVY_HTML)"
	@echo "  $(TRIVY_PDF)"
	@echo ""
	@if [[ "$(TRIVY_FAIL_ON)" != "NONE" ]]; then \
		echo "==> Trivy CI Gate: failing on $(TRIVY_FAIL_ON)+ severities"; \
		case "$(TRIVY_FAIL_ON)" in \
			CRITICAL) SEVS="CRITICAL" ;; \
			HIGH)     SEVS="HIGH,CRITICAL" ;; \
			MEDIUM)   SEVS="MEDIUM,HIGH,CRITICAL" ;; \
			LOW)      SEVS="LOW,MEDIUM,HIGH,CRITICAL" ;; \
			*) echo "ERROR: TRIVY_FAIL_ON must be NONE|LOW|MEDIUM|HIGH|CRITICAL"; exit 2 ;; \
		esac; \
		$(TRIVY) image --severity "$$SEVS" --exit-code 1 --format json -o /dev/null "$(IMAGE)" >/dev/null; \
		echo "==> Trivy gate passed"; \
	fi

$(TRIVY_JSON): | $(OUTDIR)
	@echo "==> Trivy scan: $(IMAGE)"
	# Optional noise reduction: add --ignore-unfixed
	$(TRIVY) image --format json -o "$(TRIVY_JSON)" "$(IMAGE)"
	@echo "==> JSON: $(TRIVY_JSON)"

$(TRIVY_HTML): $(TRIVY_JSON)
	@echo "==> Render Trivy HTML (display severities: $(TRIVY_REPORT_SEVERITIES))"
	$(PYTHON) "$(TRIVY_RENDER)" "$(IMAGE)" "$(TRIVY_JSON)" "$(TRIVY_HTML)" "$(TRIVY_REPORT_SEVERITIES)"
	@echo "==> HTML: $(TRIVY_HTML)"

$(TRIVY_PDF): $(TRIVY_HTML)
	@echo "==> Render Trivy PDF (Chromium headless)"
	$(CHROMIUM) --headless --disable-gpu --no-sandbox \
		--print-to-pdf="$(TRIVY_PDF)" \
		"file://$$(realpath "$(TRIVY_HTML)")" >/dev/null 2>&1 || true
	@if [[ ! -s "$(TRIVY_PDF)" ]]; then \
		echo "ERROR: Trivy PDF generation failed. Try running chromium manually:"; \
		echo "  chromium --headless --disable-gpu --no-sandbox --print-to-pdf=$(TRIVY_PDF) file://$$(realpath $(TRIVY_HTML))"; \
		exit 1; \
	fi
	@echo "==> PDF: $(TRIVY_PDF)"

clean:
	rm -rf "$(OUTDIR)"
