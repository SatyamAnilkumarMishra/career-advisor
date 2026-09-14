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

# ---------------------------------------------------------------------------
# 4. Building In-Demand Skills
# ---------------------------------------------------------------------------
story.append(h1("4. Building In-Demand Skills"))
story.append(
    p(
        "Skill-building pays off fastest when it is aimed at a specific target role rather than "
        "pursued generically. Start from the destination and work backward: pick 2-3 target job "
        "postings, list every skill they mention, and sort into skills you already have, skills "
        "you're missing, and skills you have partially."
    )
)
story.append(h2("4.1 A durable learning loop"))
story.append(
    bullets(
        [
            "Learn the minimum theory needed to start (a short course or a few chapters), then "
            "immediately apply it to a small real project — passive consumption without building "
            "something rarely sticks.",
            "Ship something visible: a repo, a write-up, a small tool, a dataset analysis. Proof "
            "of applied skill outweighs a certificate alone in almost every hiring conversation.",
            "Get feedback from someone more experienced before moving to the next skill — this "
            "is the step most self-learners skip and it's where the compounding happens.",
            "Revisit fundamentals periodically; skills decay faster than most people expect, "
            "especially tools that change quickly.",
        ]
    )
)
story.append(h2("4.2 High-durability skill categories"))
story.append(
    p(
        "Regardless of specific role, three categories consistently transfer across roles and "
        "hold their value over a career: quantitative/data reasoning (statistics, spreadsheet "
        "and SQL fluency, and interpreting data critically rather than mechanically), written "
        "and verbal communication (documenting decisions, presenting technical work to "
        "non-technical audiences), and applied AI/automation literacy (using AI tools to "
        "genuinely speed up your work, not just superficially)."
    )
)

# ---------------------------------------------------------------------------
# 5. Job Search Strategy & Networking
# ---------------------------------------------------------------------------
story.append(h1("5. Job Search Strategy &amp; Networking"))
story.append(
    p(
        "The majority of roles are filled through referrals and warm introductions rather than "
        "cold applications through job boards alone. A search strategy that relies purely on "
        "applying to postings tends to convert far worse than one that combines applications "
        "with direct outreach."
    )
)
story.append(h2("5.1 Networking that doesn't feel transactional"))
story.append(
    bullets(
        [
            "Reach out before you need something. A short, genuine message about someone's work "
            "(\"I read your post on X and had a follow-up question\") lands better than a cold "
            "ask for a referral from someone you've never spoken to.",
            "Give before you ask: share a relevant article, make an introduction, offer a piece "
            "of specific feedback. Small, low-cost favors build the relationship that makes a "
            "later ask comfortable.",
            "When you do ask for a referral, make it easy: attach your resume, a one-line pitch "
            "of why you're a fit, and the specific job link — don't make the other person do "
            "research on your behalf.",
        ]
    )
)
story.append(h2("5.2 A weekly search cadence that scales"))
story.append(
    p(
        "A sustainable structure for an active search: roughly 40% of time on targeted "
        "applications to roles you're genuinely a strong fit for, 30% on outreach and "
        "networking conversations, 20% on skill-building or portfolio work, and 10% on "
        "interview practice. Track every application in a simple spreadsheet (role, company, "
        "date applied, contact, status, follow-up date) — searches that go longer than 6-8 "
        "weeks without a tracking system tend to lose momentum and repeat wasted effort."
    )
)

# ---------------------------------------------------------------------------
# 6. Choosing and Planning a Career Path
# ---------------------------------------------------------------------------
story.append(h1("6. Choosing and Planning a Career Path"))
story.append(
    p(
        "Career direction is rarely found by introspection alone — it's found by running small, "
        "low-cost experiments and paying attention to what energizes you versus what drains you, "
        "then course-correcting. Treat the first few years of a career as a series of "
        "hypotheses to test, not a single irreversible choice."
    )
)
story.append(h2("6.1 A simple framework for evaluating a path"))
story.append(
    Table(
        [
            ["Dimension", "Questions to ask"],
            ["Interest", "Would you read about this on a Saturday out of curiosity?"],
            ["Aptitude", "Does feedback suggest you pick this up faster than peers?"],
            ["Market demand", "Are there enough open roles, in enough places, to have options?"],
            ["Trajectory", "Does 5 years in this path compound into more opportunity, or a ceiling?"],
        ],
        colWidths=[1.6 * inch, 4.4 * inch],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), "#1a1a2e"),
                ("TEXTCOLOR", (0, 0), (-1, 0), "#ffffff"),
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("GRID", (0, 0), (-1, -1), 0.5, "#cccccc"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        ),
    )
)
story.append(Spacer(1, 10))
story.append(
    p(
        "A path strong on three of the four is usually worth pursuing; a path weak on market "
        "demand and trajectory is worth treating as a hobby rather than a career bet, even if "
        "interest and aptitude are high."
    )
)
story.append(h2("6.2 Milestone-based roadmaps"))
story.append(
    p(
        "Break a target transition into 3-4 milestones spread across your timeframe rather than "
        "a single distant goal. A typical 6-month transition into a new technical role looks "
        "like: Month 1-2 close the biggest skill gaps with focused projects; Month 2-4 build "
        "2-3 portfolio pieces and start networking outreach; Month 3-5 begin applying while "
        "continuing to build; Month 5-6 concentrate on interview loops and negotiation. Review "
        "progress every 2-3 weeks and adjust the plan rather than treating the original roadmap "
        "as fixed."
    )
)

# ---------------------------------------------------------------------------
# 7. Remote & Hybrid Work
# ---------------------------------------------------------------------------
story.append(h1("7. Remote &amp; Hybrid Work Effectiveness"))
story.append(
    p(
        "Remote work removes ambient visibility, so impact has to be made legible deliberately. "
        "The professionals who thrive remotely tend to over-communicate status relative to an "
        "office norm: a short written update at the end of each day or week, decisions "
        "documented in writing rather than left in a chat thread, and questions asked in public "
        "channels so the answer helps the next person too."
    )
)
story.append(
    p(
        "For early-career remote workers specifically, proactively scheduling brief 1:1s with "
        "teammates and skip-level managers compensates for the informal hallway conversations "
        "that build visibility in an office. Being remote is not a career risk on its own; being "
        "invisible is."
    )
)

# ---------------------------------------------------------------------------
# 8. Common Pitfalls
# ---------------------------------------------------------------------------
story.append(h1("8. Common Pitfalls to Avoid"))
story.append(
    bullets(
        [
            "Applying to roles with a generic, unmodified resume — tailoring the top third "
            "meaningfully improves response rates for a few minutes of extra effort per "
            "application.",
            "Waiting to network until actively job-hunting — relationships built under urgency "
            "read as transactional and convert worse than relationships built over time.",
            "Treating a job offer's base salary as fixed and not negotiating the rest of the "
            "package (start date, signing bonus, equity, title) even when base truly is capped "
            "by a band.",
            "Learning skills in isolation from a target role, leading to a portfolio that looks "
            "impressive but doesn't map to what target employers are actually screening for.",
            "Going quiet in a remote role and letting managers assume no news is bad news — "
            "under-communication is consistently rated the top failure mode for junior remote "
            "hires.",
        ]
    )
)

story.append(Spacer(1, 16))
story.append(
    Paragraph(
        "<i>This guide is a general-purpose reference. For the highest quality guidance, "
        "combine it with specifics about your own background, target role, and location when "
        "chatting with Career Advisor.</i>",
        styles["BodyCustom"],
    )
)

doc = SimpleDocTemplate(
    OUTPUT_PATH,
    pagesize=letter,
    leftMargin=0.85 * inch,
    rightMargin=0.85 * inch,
    topMargin=0.85 * inch,
    bottomMargin=0.85 * inch,
    title="Career Advisor Guide 2025",
    author="Career Advisor",
)
doc.build(story)
print(f"Wrote {OUTPUT_PATH}")
