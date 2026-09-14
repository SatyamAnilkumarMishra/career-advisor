"""One-off script: renders the default 'Career_Advisor_Guide_2025.pdf' reference
document that backend/config.py points to (`default_document_path`).

This is the document the CLI (backend/main.py) auto-indexes into ChromaDB on
first run when no persisted vector store exists yet, and it's a reasonable
document for someone to upload via /api/documents/upload to see the RAG chat
grounded with citations. Not part of the runtime app — run once to produce
the PDF, then it just ships as a repo asset.

Usage:
    pip install reportlab   # not a runtime dependency, only needed to regenerate this PDF
    python scripts/build_default_guide.py
"""

from __future__ import annotations

import os

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUTPUT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "Career_Advisor_Guide_2025.pdf",
)

styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="H1Custom",
        parent=styles["Heading1"],
        spaceBefore=18,
        spaceAfter=10,
        textColor="#1a1a2e",
    )
)
styles.add(
    ParagraphStyle(
        name="H2Custom",
        parent=styles["Heading2"],
        spaceBefore=12,
        spaceAfter=6,
        textColor="#16213e",
    )
)
styles.add(
    ParagraphStyle(
        name="BodyCustom",
        parent=styles["Normal"],
        fontSize=10.5,
        leading=15,
        spaceAfter=8,
        alignment=TA_LEFT,
    )
)
styles.add(
    ParagraphStyle(
        name="CoverTitle",
        parent=styles["Title"],
        fontSize=28,
        leading=34,
        spaceAfter=6,
    )
)
styles.add(
    ParagraphStyle(
        name="CoverSubtitle",
        parent=styles["Normal"],
        fontSize=13,
        leading=18,
        textColor="#555555",
    )
)


def p(text: str) -> Paragraph:
    return Paragraph(text, styles["BodyCustom"])


def h1(text: str) -> Paragraph:
    return Paragraph(text, styles["H1Custom"])


def h2(text: str) -> Paragraph:
    return Paragraph(text, styles["H2Custom"])


def bullets(items: list[str]) -> ListFlowable:
    return ListFlowable(
        [ListItem(p(item), leftIndent=6) for item in items],
        bulletType="bullet",
        start="•",
        leftIndent=18,
    )


story: list = []

# ---------------------------------------------------------------------------
# Cover
# ---------------------------------------------------------------------------
story.append(Spacer(1, 1.6 * inch))
story.append(Paragraph("Career Advisor Guide", styles["CoverTitle"]))
story.append(Paragraph("A Practical Handbook for Students &amp; Early-Career Professionals", styles["CoverSubtitle"]))
story.append(Spacer(1, 0.4 * inch))
story.append(
    Paragraph(
        "2025 Edition &nbsp;|&nbsp; Resumes &amp; ATS &nbsp;|&nbsp; Interviews &amp; Negotiation "
        "&nbsp;|&nbsp; Skill-Building &nbsp;|&nbsp; Job Search &amp; Networking &nbsp;|&nbsp; Career Roadmaps",
        styles["Normal"],
    )
)
story.append(PageBreak())

# ---------------------------------------------------------------------------
# 1. Building a Resume That Passes ATS and Convinces Humans
# ---------------------------------------------------------------------------
story.append(h1("1. Building a Resume That Passes ATS and Convinces Humans"))
story.append(
    p(
        "Most mid-size and large employers route incoming resumes through an Applicant "
        "Tracking System (ATS) before a human ever sees them. The ATS parses your document "
        "into structured fields and, in many pipelines, scores it against the keywords in the "
        "job description. A resume can be a strong professional document and still fail this "
        "step if it is built the wrong way."
    )
)
story.append(h2("1.1 Formatting rules that keep you machine-readable"))
story.append(
    bullets(
        [
            "Use a single-column layout. Multi-column and text-box layouts frequently parse "
            "out of order or drop content entirely.",
            "Save as .docx or a text-based PDF (never a scanned image). Avoid headers/footers "
            "for anything the ATS needs to read, since many parsers skip them.",
            "Use standard section headings: \"Experience\", \"Education\", \"Skills\", "
            "\"Projects\" — creative headings like \"Where I've Made Impact\" can confuse parsers.",
            "Spell out acronyms at least once (\"Search Engine Optimization (SEO)\") so keyword "
            "matching catches both forms.",
            "Avoid tables, icons, and graphics for core content; a skills-icon row looks nice "
            "but often extracts as blank space.",
        ]
    )
)
story.append(h2("1.2 Writing bullets that convince a human reader"))
story.append(
    p(
        "Once a resume clears the ATS, a recruiter typically spends well under a minute on the "
        "first pass. Every bullet should lead with a strong action verb and, wherever possible, "
        "quantify the result. The most reliable structure is the "
        "<b>Action + Task + Result</b> pattern: what you did, on what, and what changed because "
        "of it."
    )
)
story.append(
    bullets(
        [
            "Weak: \"Responsible for managing social media accounts.\"",
            "Strong: \"Grew Instagram engagement 42% in 3 months by launching a weekly "
            "student-spotlight series, adding 1,800 followers.\"",
            "Weak: \"Worked on backend features for the checkout flow.\"",
            "Strong: \"Rebuilt the checkout API's retry logic, cutting failed-payment "
            "support tickets by 30% over one quarter.\"",
        ]
    )
)
story.append(h2("1.3 Tailoring per application"))
story.append(
    p(
        "Keep one detailed master resume that lists everything, then trim and reorder it per "
        "application so the top third of the page matches the job description's priorities. "
        "Mirror the exact phrasing the posting uses for your core skills (\"stakeholder "
        "management\" vs. \"cross-functional collaboration\") — ATS keyword matching is "
        "usually literal, not semantic."
    )
)

# ---------------------------------------------------------------------------
# 2. Interview Preparation
# ---------------------------------------------------------------------------
story.append(h1("2. Interview Preparation"))
story.append(h2("2.1 Behavioral interviews and the STAR method"))
story.append(
    p(
        "Behavioral questions (\"Tell me about a time you disagreed with a teammate\") are best "
        "answered with the STAR structure: <b>Situation</b> (brief context), <b>Task</b> (what "
        "you were responsible for), <b>Action</b> (what you specifically did — use \"I\", not "
        "\"we\"), and <b>Result</b> (the measurable or observable outcome, plus what you learned)."
    )
)
story.append(
    p(
        "Prepare 6-8 STAR stories before any interview cycle, covering: a conflict you "
        "resolved, a failure or mistake you owned, a time you influenced without authority, a "
        "project under a tight deadline, a time you used data to change a decision, and a time "
        "you mentored or helped someone else succeed. Most behavioral questions map onto one of "
        "these even when phrased differently."
    )
)
story.append(h2("2.2 Technical and case interviews"))
story.append(
    p(
        "For technical roles, practice explaining your reasoning out loud, not just producing a "
        "correct answer — interviewers are evaluating your problem-solving process as much as "
        "the result. Clarify constraints before coding or modeling, state your approach before "
        "diving in, narrate trade-offs as you go, and test your solution against an edge case "
        "at the end rather than assuming it's correct."
    )
)
story.append(h2("2.3 Questions to ask the interviewer"))
story.append(
    bullets(
        [
            "\"What does success look like in this role at the 90-day mark?\"",
            "\"What's the biggest challenge someone in this seat would face in the first six months?\"",
            "\"How does the team decide what to work on — and how much of that plan tends to survive contact with reality?\"",
            "\"What would make you excited about a candidate versus merely satisfied?\"",
        ]
    )
)
story.append(
    p(
        "Avoid questions answered on the company's public website — it signals you didn't "
        "prepare. Save compensation and time-off questions for after an offer is on the table "
        "unless the recruiter raises them first."
    )
)

# ---------------------------------------------------------------------------
# 3. Salary Negotiation
# ---------------------------------------------------------------------------
story.append(h1("3. Salary Negotiation"))
story.append(
    p(
        "Negotiation is expected in most markets and most offers have room built in. Declining "
        "to negotiate almost never helps your candidacy, and in the large majority of cases "
        "costs nothing to try respectfully."
    )
)
story.append(h2("3.1 Before you get an offer"))
story.append(
    bullets(
        [
            "Research market rate using multiple sources (public salary-transparency data, "
            "level-normalized comparison sites, and conversations with people in similar roles) "
            "rather than a single number.",
            "If asked for salary expectations early, give a researched range rather than a "
            "single figure, and anchor it to the role's level rather than your last salary.",
            "Let the employer name a number first whenever possible — negotiating range vs. "
            "range is easier than negotiating up from a number you offered.",
        ]
    )
)
story.append(h2("3.2 Once you have an offer"))
story.append(
    p(
        "Thank them, express genuine enthusiasm, and ask for a short window (24-72 hours is "
        "normal) to review. Negotiate the full package, not just base salary — signing bonus, "
        "equity, start date, remote/relocation terms, and title can all move even when base is "
        "fixed by a pay band. Competing offers are the single strongest lever; if you have one, "
        "say so factually without bluffing."
    )
)
story.append(
    p(
        "A simple, effective script: \"I'm excited about this role and the team. Based on my "
        "research and experience, I was hoping for something closer to $X. Is there flexibility "
        "there?\" Silence after making an ask is a negotiating tool, not a mistake — resist the "
        "urge to fill it."
    )
)
