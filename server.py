import os
import re
import smtplib
import pytesseract
import pdf2image
import cv2
import numpy as np
from fpdf import FPDF
from flask import Flask, request, jsonify, send_file
from email.message import EmailMessage
from unidecode import unidecode
from datetime import datetime

app = Flask(__name__)

# ✅ Load Email Credentials from Environment Variables
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "info@mytips.pro")
EMAIL_AUTH_USER = os.getenv("EMAIL_AUTH_USER", "leif@mytips.pro")  # Login email
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", 465))

# ✅ Helper function to clean text (removes unsupported characters)
def clean_text(text):
    """ Remove unsupported characters and force ASCII encoding """
    return unidecode(str(text))  # Converts special characters to closest ASCII match

# ✅ OCR Extraction Function
def extract_text_from_pdf(pdf_path):
    """ Extracts text from the given PDF using OCR """
    try:
        print(f"📄 Processing PDF: {pdf_path}")
        images = pdf2image.convert_from_path(pdf_path)
        extracted_text = ""

        for i, image in enumerate(images):
            print(f"📸 Extracting text from page {i+1}...")
            text = pytesseract.image_to_string(image)
            extracted_text += text + "\n"

        print(f"✅ OCR Extraction Complete! Extracted Text:\n{text}")
        return extracted_text
    except Exception as e:
        print(f"❌ OCR Extraction Failed: {e}")
        return None

# ✅ Email Sending Function
def send_email_with_attachment(to_email, pdf_path):
    """ Sends an email with the compliance report attached """
    try:
        msg = EmailMessage()
        msg["Subject"] = "Your Pay Stub Compliance Report"
        msg["From"] = EMAIL_SENDER
        msg["To"] = to_email
        msg.set_content("Attached is your compliance report. Please review it.")

        with open(pdf_path, "rb") as f:
            msg.add_attachment(f.read(), maintype="application", subtype="pdf", filename=os.path.basename(pdf_path))

        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(EMAIL_AUTH_USER, EMAIL_PASSWORD)
            server.send_message(msg)

        print(f"✅ Email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

# ✅ Pay Stub Processing Route
@app.route("/process-paystub", methods=["POST"])
def process_paystub():
    try:
        data = request.json
        file_url = data.get("file_url")
        email = data.get("email")

        if not file_url or not email:
            return jsonify({"error": "Missing required fields"}), 400

        # ✅ Download PDF (Simulated - replace this with actual file handling)
        pdf_path = "uploaded_paystub.pdf"

        # ✅ Extract text from PDF
        extracted_text = extract_text_from_pdf(pdf_path)
        if not extracted_text:
            return jsonify({"error": "OCR failed to extract pay stub data"}), 500

        # ✅ Extract relevant info using regex
        employee_name_match = re.search(r"EMPLOYEE\s+([\w\s]+)", extracted_text)
        reported_wages_match = re.search(r"NET PAY:\s*\$([\d,]+.\d{2})", extracted_text)
        hours_match = re.search(r"Total Hours:\s*([\d.]+)", extracted_text)

        employee_name = employee_name_match.group(1).strip() if employee_name_match else "Unknown Employee"
        reported_wages = float(reported_wages_match.group(1).replace(",", "")) if reported_wages_match else 0.00
        total_hours = float(hours_match.group(1)) if hours_match else 0.00

        # ✅ Compliance Check Logic
        calculated_wages = reported_wages * 1.05  # Simulated Calculation
        tip_credit_valid = reported_wages >= 100  # Fake check for demo
        overtime_valid = total_hours <= 40  # Fake check for demo
        status = "✅ Wages Match!" if reported_wages == calculated_wages else "⚠️ Mismatch Detected!"

        # ✅ Generate PDF Report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"paystub_report_{timestamp}.pdf"
        pdf_path = os.path.join(os.getcwd(), pdf_filename)

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", style="", size=12)

        # ✅ Add Logo (if available)
        logo_path = "static/checkmychecks_logo.png"
        if os.path.exists(logo_path):
            pdf.image(logo_path, x=10, y=8, w=40)
        else:
            print("⚠️ WARNING: Logo file not found, skipping logo.")

        # ✅ Title
        pdf.set_xy(60, 10)
        pdf.set_font("Arial", style="B", size=16)
        pdf.cell(200, 10, "Pay Stub Compliance Report", ln=True, align="L")
        pdf.ln(10)

        # ✅ Employee Information
        pdf.set_font("Arial", style="B", size=12)
        pdf.cell(200, 10, f"Employee: {clean_text(employee_name)}", ln=True)
        pdf.ln(5)

        # ✅ Table Headers
        pdf.set_font("Arial", style="B", size=10)
        pdf.cell(90, 10, "Expected Value", border=1, align="C")
        pdf.cell(90, 10, "Reported Value", border=1, align="C")
        pdf.ln()

        # ✅ Table Data (Wages)
        pdf.set_font("Arial", size=10)
        pdf.cell(90, 10, f"Calculated Wages: ${calculated_wages:.2f}", border=1, align="C")
        pdf.cell(90, 10, f"Reported Wages: ${reported_wages:.2f}", border=1, align="C")
        pdf.ln()

        # ✅ Compliance Check - Tip Credit
        pdf.cell(90, 10, "Tip Credit Compliance", border=1, align="C")
        pdf.cell(90, 10, "✅ Valid" if tip_credit_valid else "⚠️ Issue Detected", border=1, align="C")
        pdf.ln()

        # ✅ Compliance Check - Overtime
        pdf.cell(90, 10, "Overtime Compliance", border=1, align="C")
        pdf.cell(90, 10, "✅ Valid" if overtime_valid else "⚠️ Issue Detected", border=1, align="C")
        pdf.ln()

        # ✅ Summary Status
        pdf.set_font("Arial", style="B", size=12)
        pdf.cell(200, 10, f"Status: {clean_text(status)}", ln=True, align="L")

        # ✅ Save PDF
        pdf.output(pdf_path, "F")
        print(f"✅ PDF file successfully created at {pdf_path}")

        # ✅ Send Email with Attachment
        email_success = send_email_with_attachment(email, pdf_path)
        if not email_success:
            return jsonify({"error": "Report generated but email failed"}), 500

        return send_file(pdf_path, mimetype="application/pdf", as_attachment=True)

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

# ✅ Run Flask App
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
