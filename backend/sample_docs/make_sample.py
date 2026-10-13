"""Builds sample_docs/aurora_handbook.pdf, an invented employee handbook used for demos and the
retrieval evaluation. Aurora Labs is a fictional company. Run: python sample_docs/make_sample.py"""
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

SECTIONS = [
    ("1. Welcome to Aurora Labs", [
        "Aurora Labs builds scheduling software for clinics and hospitals. The company was founded in 2019 in Pune and now has offices in Pune and Hyderabad.",
        "This handbook explains how we work, what we offer and what we expect. If something here is unclear, ask your manager or write to people@auroralabs.example.",
        "Our working week runs from Monday to Friday. Core collaboration hours are 11:00 to 16:00 IST, when everyone should be reachable. Outside core hours you can plan your own time.",
    ]),
    ("2. Leave and holidays", [
        "Every full-time employee receives 24 days of paid annual leave per calendar year, in addition to 10 public holidays. Up to 8 unused leave days can be carried over to the next year; any extra unused days lapse on 31 March.",
        "Sick leave is separate from annual leave. You get 12 days of paid sick leave a year. For an absence of more than 2 consecutive days, please share a medical certificate with the people team.",
        "Parental leave is 26 weeks for the primary caregiver and 4 weeks for the secondary caregiver, both fully paid. Parental leave can start up to 4 weeks before the expected date of birth or adoption.",
        "Leave requests go through the HR portal. Requests of 5 days or more need approval at least 2 weeks in advance.",
    ]),
    ("3. Remote work and equipment", [
        "Aurora Labs is remote-friendly. You may work from home up to 3 days a week; teams agree their office days together. Fully remote arrangements need written approval from a department head.",
        "New employees receive a laptop on their first day. Engineers get a 16 GB laptop and a second monitor; everyone else gets a standard 8 GB laptop. Laptops are refreshed every 3 years.",
        "Each employee may claim a one-time home-office allowance of Rs 15,000 for a chair, desk or headset. Claims must be submitted with receipts within 60 days of joining.",
        "Internet costs are reimbursed up to Rs 1,000 a month for employees who work from home at least 2 days a week.",
    ]),
    ("4. Pay, expenses and travel", [
        "Salaries are paid on the last working day of each month. Payslips are available in the HR portal on the same day.",
        "Business expenses must be submitted within 30 days with a receipt. Expenses under Rs 2,000 are approved by your manager; anything above Rs 2,000 also needs approval from finance.",
        "For work travel, book economy class for flights under 6 hours. Hotel stays are covered up to Rs 6,500 a night in metro cities and Rs 4,500 a night elsewhere. The daily meal allowance on trips is Rs 1,200.",
        "Performance reviews take place twice a year, in April and October. Salary revisions are announced after the April review and take effect from 1 July.",
    ]),
    ("5. Learning and growth", [
        "Each employee has a yearly learning budget of Rs 40,000 for courses, books, certifications and conferences. Unused budget does not carry over.",
        "Engineers can spend every other Friday afternoon on learning time or internal tools. We call this Build Friday.",
        "New joiners are paired with a buddy for their first 90 days. The probation period is 6 months, with a check-in at 3 months.",
        "Internal job moves are encouraged after 12 months in a role. Talk to your manager first, then apply through the internal jobs board.",
    ]),
    ("6. Security and conduct", [
        "Use the company password manager for every work account and turn on two-factor authentication everywhere it is offered.",
        "Never share customer data outside approved tools. Patient information must stay inside the production environment and must never be copied to laptops, chat messages or personal email.",
        "Report a lost or stolen device to security@auroralabs.example within 1 hour so it can be locked remotely. Suspected phishing emails should be forwarded to the same address.",
        "Harassment and discrimination are not tolerated. Concerns can be raised with your manager, the people team or anonymously through the ethics line, and will be investigated within 10 working days.",
    ]),
]


def build(path: Path) -> None:
    styles = getSampleStyleSheet()
    story = [Paragraph("Aurora Labs Employee Handbook", styles["Title"]),
             Paragraph("Version 3.2, effective 1 January 2026. Aurora Labs is a fictional company created for this demo.", styles["Italic"]),
             Spacer(1, 12)]
    for i, (title, paragraphs) in enumerate(SECTIONS):
        if i:
            story.append(PageBreak())
        story.append(Paragraph(title, styles["Heading1"]))
        for p in paragraphs:
            story.append(Paragraph(p, styles["BodyText"]))
            story.append(Spacer(1, 6))
    SimpleDocTemplate(str(path), pagesize=A4, title="Aurora Labs Employee Handbook").build(story)


if __name__ == "__main__":
    out = Path(__file__).with_name("aurora_handbook.pdf")
    build(out)
    print("wrote", out)
