"""
Update hermes_project_context.md with live data from Neon.

Run from project root:
    python scripts/update_hermes_context.py

Requires DATABASE_URL environment variable pointing to Neon.
Reads the current context file, updates dynamic sections, writes it back.
"""
import os
import sys
import re
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

CONTEXT_FILE = os.path.join(
    os.path.dirname(__file__), "..", "docs", "agent", "hermes_project_context.md"
)


def get_evidence_counts():
    """Query Neon for live evidence status counts."""
    try:
        from sqlalchemy import create_engine, text

        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            print("  WARNING: DATABASE_URL not set — skipping live evidence query.")
            return None

        engine = create_engine(db_url, pool_pre_ping=True)
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT evidence_status, COUNT(*) as cnt "
                    "FROM material_library "
                    "GROUP BY evidence_status "
                    "ORDER BY evidence_status"
                )
            ).fetchall()
            cats = conn.execute(
                text(
                    "SELECT evidence_category, COUNT(*) as cnt, "
                    "STRING_AGG(name, ', ' ORDER BY name) as names "
                    "FROM material_library "
                    "GROUP BY evidence_category "
                    "ORDER BY evidence_category"
                )
            ).fetchall()

        counts = {r[0]: r[1] for r in rows}
        categories = {r[0]: (r[1], r[2]) for r in cats}
        return counts, categories
    except Exception as e:
        print(f"  WARNING: Could not query database — {e}")
        return None


def build_evidence_table(counts, categories):
    """Build the evidence status markdown table."""
    today = date.today().isoformat()

    verified = counts.get("verified", 0)
    partial = counts.get("partial", 0)
    provisional = counts.get("provisional", 0)
    missing = counts.get("missing", 0)

    # Get verified material names
    _, cat_data = categories if isinstance(categories, tuple) else (None, {})

    lines = [
        f"## Current Material Evidence Status (as of {today})",
        "",
        "| Status | Count | Notes |",
        "|---|---|---|",
        f"| Verified | {verified} | Confirmed supplier + datasheet + DoP |",
        f"| Partial | {partial} | Some evidence missing (datasheet or DoP) |",
        f"| Provisional | {provisional} | Assembly/calculation rows — no DoP required |",
        f"| Missing | {missing} | No evidence yet — raw commodity items or unselected products |",
        "",
        "Evidence seed script: backend/seeds/material_evidence_seed.py",
        "Run with: python seeds/material_evidence_seed.py --force",
    ]
    return "\n".join(lines)


def update_context_file(evidence_section: str, today: str):
    """Read context file, replace dynamic sections, write back."""
    with open(CONTEXT_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # Update the date header
    content = re.sub(
        r"# Last updated: \d{4}-\d{2}-\d{2}",
        f"# Last updated: {today}",
        content,
    )

    # Replace the evidence status section
    content = re.sub(
        r"## Current Material Evidence Status.*?(?=\n---|\n## )",
        evidence_section + "\n",
        content,
        flags=re.DOTALL,
    )

    with open(CONTEXT_FILE, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    today = date.today().isoformat()
    print(f"Updating hermes_project_context.md — {today}")

    result = get_evidence_counts()

    if result:
        counts, categories = result
        print(f"  Evidence counts from Neon: {dict(counts)}")
        evidence_section = build_evidence_table(counts, categories)
    else:
        print("  Using placeholder evidence section (no DB connection).")
        evidence_section = (
            f"## Current Material Evidence Status (as of {today})\n\n"
            "| Status | Count | Notes |\n"
            "|---|---|---|\n"
            "| Verified | — | Run with DATABASE_URL set to get live counts |\n"
            "| Partial | — | — |\n"
            "| Provisional | — | — |\n"
            "| Missing | — | — |\n\n"
            "Evidence seed script: backend/seeds/material_evidence_seed.py\n"
            "Run with: python seeds/material_evidence_seed.py --force"
        )

    update_context_file(evidence_section, today)
    print(f"  Written: {CONTEXT_FILE}")
    print("Done. Commit with: git add docs/agent/hermes_project_context.md && git commit -m 'docs: update Hermes context'")


if __name__ == "__main__":
    main()
