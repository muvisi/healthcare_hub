# utils.py or any file in your Django app
from django.core.mail import send_mail
from django.conf import settings
from celery import shared_task

# @shared_task
def send_test_email(value):
    """
    Sends a test email using Django's SMTP settings.
    """
    subject = "Schemes Sfound are -{{value}}"
    message = "The cron job to sync schemes is set up correctly and this is a test email."
    from_email = settings.EMAIL_HOST_USER
    recipient_list = ["mwangangimuvisi@gmail.com"]

    try:
        send_mail(subject, message, from_email, recipient_list, fail_silently=False)
        print(f"Test email sent successfully to {recipient_list[0]}")
        return True
    except Exception as e:
        print("Failed to send test email:", e)
        return False
