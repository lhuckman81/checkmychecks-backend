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
from unidecode import unidecode  # Ensure this is installed in requirements.txt

app = Flask(__name__)

# ✅ Load Email Credentials from Render Environment Variables
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "info@mytips.pro")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", 465))

# ✅ Helper function to clean text (removes unsupported characters)
def clean_text(text):
    """ Remove unsupported characters and force ASCII encoding """
    return unidecode(str(text))  # Converts special characters to closest ASCII match

# ✅ Email Sending Function
def send_email_with_attachment(to_email, pdf_path):
    try:
        msg = EmailMessage()
        msg["Subject"] = "Your Pay Stub Compliance Report"
        msg["From"] = EMAIL_SENDER
        msg["To"] = to_email
        msg.set_content("Attached is your compliance report. Please review it.")

        with open(pdf_path, "rb") as f:
            msg.add_attachment(f.read(), maintype="application", subtype="pdf", filename=os.path.basename(pdf_path))

        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)

        print(f"✅ Email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

# ✅ Home Route
@app.route("/", methods=["GET"])
def home():
    return "Flask App is Running on Render!"

# ✅ Pay Stub Processing Route
@app.route("/process-paystub", methods=["POST"])
def process_paystub():
    try:
        data = request.json
        file_url = data.get("file_url")
        email = data.get("email")

        if not file_url or not email:
            return jsonify({"error": "Missing required fields"}), 400

        # Simulated pay stub data for testing
        employee_name = "John Doe 😃"  # Intentional emoji to test encoding fix
        reported_wages = 1500.00
        calculated_wages = 1525.00
        tip_credit_valid = False  
        overtime_valid = True  
        status = "✅ Wages Match!" if reported_wages == calculated_wages else "⚠️ Mismatch Detected!"

        # ✅ Ensure text is clean before adding to PDF
        clean_employee_name = clean_text(employee_name)
        clean_status = clean_text(status)

        # ✅ Set PDF Path
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"paystub_report_{timestamp}.pdf"
        pdf_path = os.path.join(os.getcwd(), pdf_filename)

        # ✅ Generate PDF Report
        pdf = FPDF()
        pdf.add_page()

        # ✅ Add Logo (Adjusted for Spacing)
        logo_path = "static/checkmychecks_logo.png"
        if os.path.exists(logo_path):
            pdf.image(logo_path, x=10, y=10, w=40)  # Adjusted for better positioning
        else:
            print("⚠️ WARNING: Logo file not found, skipping logo.")

        # ✅ Title (Moved Down to Avoid Overlap)
        pdf.set_font("Arial", style="B", size=16)
        pdf.set_xy(60, 15)  # Moved title below logo
        pdf.cell(200, 10, clean_text("Pay Stub Compliance Report"), ln=True, align="L")

        pdf.ln(20)  # Added space after title for clarity

        # ✅ Employee Information
        pdf.set_font("Arial", style="B", size=12)
        pdf.cell(200, 10, f"Employee: {clean_employee_name}", ln=True)

        pdf.ln(5)  

        # ✅ Table Headers (Aligned for Readability)
        pdf.set_font("Arial", style="B", size=10)
        pdf.cell(95, 10, clean_text("Expected Value"), border=1, align="C")
        pdf.cell(95, 10, clean_text("Reported Value"), border=1, align="C")
        pdf.ln()

        # ✅ Table Data (Aligned)
        pdf.set_font("Arial", size=10)
        pdf.cell(95, 10, clean_text(f"Calculated Wages: ${calculated_wages}"), border=1, align="C")
        pdf.cell(95, 10, clean_text(f"Reported Wages: ${reported_wages}"), border=1, align="C")
        pdf.ln()

        # ✅ Compliance Check - Tip Credit
        pdf.cell(95, 10, clean_text("Tip Credit Compliance"), border=1, align="C")
        pdf.cell(95, 10, clean_text("✅ Valid" if tip_credit_valid else "⚠️ Issue Detected"), border=1, align="C")
        pdf.ln()

        # ✅ Compliance Check - Overtime
        pdf.cell(95, 10, clean_text("Overtime Compliance"), border=1, align="C")
        pdf.cell(95, 10, clean_text("✅ Valid" if overtime_valid else "⚠️ Issue Detected"), border=1, align="C")
        pdf.ln()

        # ✅ Summary Status (Spacing Improved)
        pdf.set_font("Arial", style="B", size=12)
        pdf.ln(5)
        pdf.cell(200, 10, f"Status: {clean_status}", ln=True, align="L")

        # ✅ Save PDF
        print(f"📂 Attempting to save PDF to: {pdf_path}")
        pdf.output(pdf_path, "F")

        # ✅ Validate PDF Creation
        if not os.path.exists(pdf_path):
            print(f"❌ ERROR: PDF file was NOT created at {pdf_path}")
            return jsonify({"error": "PDF file was not generated"}), 500

        file_size = os.path.getsize(pdf_path)
        if file_size < 500:  # Less than 500 bytes is suspicious
            print(f"❌ ERROR: PDF file is too small ({file_size} bytes). It may be corrupted.")
            return jsonify({"error": "PDF file is invalid"}), 500

        print(f"✅ PDF file successfully created at {pdf_path}, size: {file_size} bytes")

        # ✅ Send Email with Attachment
        email_success = send_email_with_attachment(email, pdf_path)
        if not email_success:
            return jsonify({"error": "Report generated but email failed"}), 500

        # ✅ Return the PDF file
        return send_file(pdf_path, mimetype="application/pdf", as_attachment=True)

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

# ✅ Ensure Flask runs correctly on Render
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
