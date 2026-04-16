"""Generate a PDF summary report for a Site Ripper job via reportlab."""
from datetime import datetime
from pathlib import Path
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024
    return f"{n:.1f} TB"


def build_report(
    path: Path,
    *,
    job_url: str,
    stats: dict,
    by_kind: dict[str, dict],
    broken: Iterable[dict],
) -> None:
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    h1 = styles["Heading1"]
    h2 = styles["Heading2"]
    body = styles["BodyText"]
    mono = ParagraphStyle(
        "mono",
        parent=body,
        fontName="Courier",
        fontSize=9,
        leading=12,
    )

    story = []
    story.append(Paragraph("Site Ripper — Mirror Report", h1))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(f"<b>Source:</b> {job_url}", body))
    story.append(Paragraph(f"<b>Generated:</b> {datetime.utcnow().isoformat()}Z", body))
    story.append(Spacer(1, 0.6 * cm))

    story.append(Paragraph("Summary", h2))
    summary_rows = [
        ["Metric", "Value"],
        ["Pages crawled", str(stats.get("pages", 0))],
        ["Assets downloaded", str(stats.get("assets", 0))],
        ["Total bytes", _fmt_bytes(stats.get("bytes_total", 0))],
        ["Broken", str(stats.get("broken", 0))],
        ["Failed", str(stats.get("failed", 0))],
    ]
    t = Table(summary_rows, hAlign="LEFT", colWidths=[5 * cm, 5 * cm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e2029")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#94a3b8")),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 0.6 * cm))

    story.append(Paragraph("Breakdown by asset type", h2))
    kind_rows = [["Kind", "Count", "Bytes"]]
    for kind, data in sorted(by_kind.items(), key=lambda kv: -kv[1].get("bytes", 0)):
        kind_rows.append(
            [kind, str(data.get("count", 0)), _fmt_bytes(data.get("bytes", 0))]
        )
    t2 = Table(kind_rows, hAlign="LEFT", colWidths=[4 * cm, 3 * cm, 4 * cm])
    t2.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e2029")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#94a3b8")),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(t2)
    story.append(Spacer(1, 0.6 * cm))

    broken_list = list(broken)
    if broken_list:
        story.append(Paragraph(f"Broken assets ({len(broken_list)})", h2))
        for b in broken_list[:200]:
            story.append(
                Paragraph(
                    f"[{b.get('status','?')}] {b.get('url','')}",
                    mono,
                )
            )
    else:
        story.append(Paragraph("No broken assets.", body))

    doc.build(story)
