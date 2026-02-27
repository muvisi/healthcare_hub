# jobs/test_email.py
import os
import django
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.timezone import now

# 1️⃣ Set Django settings module and setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "healthcare_hub.settings")
django.setup()

# 2️⃣ Email function
def send_test_email():
    subject = "✅ Test Members Sync Email - Madison Healthcare"
    from_email = "haisnotifications@madison.co.ke"
    to_email = ["mwangangimuvisi@gmail.com"]

    # Example member data
    members = [
        {"member_no": "M001", "surname": "Doe", "first_name": "John", "status": "Success"},
        {"member_no": "M002", "surname": "Smith", "first_name": "Jane", "status": "Failed"},
    ]

    html_content = render_to_string(
        "test.html",
        {"members": members, "success_count": 1, "failed_count": 1, "now": now()},
    )

    msg = EmailMultiAlternatives(subject, "", from_email, to_email)
    msg.attach_alternative(html_content, "text/html")
    msg.send()
    print(f"Email sent successfully to {', '.join(to_email)}")

# 3️⃣ Run
if __name__ == "__main__":
    send_test_email()