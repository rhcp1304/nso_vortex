# meeting_analyzer/workflows/report_generator.py

from fpdf import FPDF
from typing import Dict, Any


def generate_pdf_report(analysis_report: Dict[str, Any], output_path: str):
    """Formats the structured analysis report into a PDF file and saves it."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_fill_color(220, 220, 220)
    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 12, "Team Meeting Analysis Report", 0, 1, "C", fill=True)
    pdf.ln(5)

    # Property Data Section
    pdf.set_font("Arial", "B", 14)
    pdf.set_text_color(40, 40, 200)
    pdf.cell(0, 10, "Property Data", 0, 1)
    pdf.set_text_color(0, 0, 0)

    pdf.set_font("Arial", "", 10)
    data = analysis_report.get("property_data", {})
    if data:
        for key, value in data.items():
            pdf.cell(40, 6, f"{key}:", 0, 0, 'L')
            pdf.cell(0, 6, value, 0, 1, 'L')
    else:
        pdf.multi_cell(0, 5, "Property data not found in analysis report.")

    pdf.ln(3)

    # Summary Section
    pdf.set_font("Arial", "B", 14)
    pdf.set_text_color(40, 40, 200)
    pdf.cell(0, 10, "1. Summary of Key Topics", 0, 1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 5, analysis_report.get("summary", "N/A"))
    pdf.ln(3)

    # Action Items Section
    pdf.set_font("Arial", "B", 14)
    pdf.set_text_color(40, 40, 200)
    pdf.cell(0, 10, "2. Action Items & Tasks Assigned", 0, 1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "", 10)
    action_items = analysis_report.get("action_items", [])
    if action_items:
        for item in action_items:
            pdf.multi_cell(0, 5, f"- {item}")
    else:
        pdf.multi_cell(0, 5, "No specific action items or tasks were assigned.")
    pdf.ln(3)

    # Final Decision Section
    pdf.set_font("Arial", "B", 14)
    pdf.set_text_color(40, 40, 200)
    pdf.cell(0, 10, "3. Final Decision", 0, 1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 12)
    pdf.multi_cell(0, 6, analysis_report.get("final_decision", "Decision not concluded."))

    pdf.output(output_path)