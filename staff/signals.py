# newproject/staff/signals.py

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model # To get the current user model if needed

from .audit_logger import log_audit_action
from .models import (
    emp_registers, Project, LeaveRecord,
    Handbook, Acknowledgment, Timesheet, Holiday,
    Resignation, ResignStatusAction, SentEmail,
)

# Helper to get identifier from request.session if available, else from user object
def get_signal_audit_identifier(request=None, user=None, instance=None):
    if request and request.session.get('name'):
        return request.session.get('name')
    if user and user.is_authenticated:
        return user.name # Assuming 'name' is a field on your emp_registers user model
    if instance and hasattr(instance, 'name'): # Fallback for model instances directly
        return instance.name
    if instance and hasattr(instance, 'employee') and instance.employee and hasattr(instance.employee, 'name'):
        return instance.employee.name
    if instance and hasattr(instance, 'emp_id') and instance.emp_id and hasattr(instance.emp_id, 'name'):
        return instance.emp_id.name
    return "System/Unknown"


# --- User Authentication Signals ---
@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    # Here, request is available, so we can use request.session.name
    identifier = get_signal_audit_identifier(request=request, user=user)
    print(f"DEBUG: Signal 'user_logged_in' received for {identifier}")
    log_audit_action(identifier, "logged in")

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    # Here, request is available, so we can use request.session.name
    identifier = get_signal_audit_identifier(request=request, user=user)
    print(f"DEBUG: Signal 'user_logged_out' received for {identifier}")
    log_audit_action(identifier, "logged out")
# -----------------------------------

# --- Model Operation Signals (NO request.session.name available here) ---
# For these, we must use identifiers available on the model instance itself.

@receiver(post_save, sender=emp_registers)
def log_emp_registers_save(sender, instance, created, **kwargs):
    action = "created new employee" if created else "Login "
    # Cannot get request.session.name here. Use instance's own name/email
    identifier = instance.name # Or instance.email or instance.pk
    print(f"DEBUG: Signal 'post_save' for emp_registers (ID: {instance.pk})")
    log_audit_action(identifier, f"{action} for {instance.name} (ID: {instance.pk})")
# in signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Handbook

@receiver(post_save, sender=Handbook)
def process_handbook_on_upload(sender, instance, created, **kwargs):
    if created:
        print(f"[AI Chatbot] Processing handbook: {instance.document_name}")
        count = instance.process_for_chatbot()
        print(f"[AI Chatbot] {count} chunks embedded.")



@receiver(post_save, sender=Project)
def log_project_save(sender, instance, created, **kwargs):
    action = "created project" if created else "updated project"
    print(f"DEBUG: Signal 'post_save' for Project (ID: {instance.pk})")
    # Identify the user who created/updated if possible, otherwise System/Unknown
    # If a Project has a 'created_by' or 'updated_by' ForeignKey to emp_registers, use that.
    # Otherwise, you can't link it to the current session user directly.
    user_who_acted = "System/Unknown" # Fallback if no direct link
    if hasattr(instance, 'emp_id') and instance.emp_id: # Assuming emp_id is the project lead/owner
        user_who_acted = instance.emp_id.name
    # Or if you have a `modified_by` or `created_by` field (recommended for audit trails)
    # if hasattr(instance, 'modified_by') and instance.modified_by:
    #     user_who_acted = instance.modified_by.name

    log_audit_action(user_who_acted, f"{action} '{instance.pname}' (ID: {instance.pk})")


@receiver(post_save, sender=LeaveRecord)
def log_leave_record_save(sender, instance, created, **kwargs):
    # This signal might be triggered by an employee applying OR by HR approving/rejecting.
    # To log who *performed* the action, you'd need the request object.
    # For now, we log it in relation to the employee whose leave it is.
    action = "applied for leave" if created else "updated leave application"
    print(f"DEBUG: Signal 'post_save' for LeaveRecord (ID: {instance.pk})")
    identifier = instance.emp_id.name if instance.emp_id else "System/Unknown"
    log_audit_action(identifier, f"{action} of type '{instance.leave_type.name}' with status '{instance.approval_status.status}' (ID: {instance.pk})")

# ... (add similar post_save/post_delete receivers for other models you need to audit) ...

@receiver(post_save, sender=Resignation)
def log_resignation_save(sender, instance, created, **kwargs):
    action = "submitted resignation" if created else "updated resignation"
    print(f"DEBUG: Signal 'post_save' for Resignation (ID: {instance.pk})")
    identifier = instance.employee.name if instance.employee else "System/Unknown"
    log_audit_action(identifier, f"{action} with status '{instance.resign_status.status_name}' (ID: {instance.pk})")

@receiver(post_save, sender=ResignStatusAction)
def log_resign_status_action_save(sender, instance, created, **kwargs):
    print(f"DEBUG: Signal 'post_save' for ResignStatusAction (ID: {instance.pk})")
    # This is typically an HR action
    identifier = instance.action_by.name if instance.action_by else "System/Unknown"
    log_audit_action(identifier, f"recorded resignation action '{instance.action}' for {instance.resignation.employee.name} (ID: {instance.pk})")

@receiver(post_save, sender=SentEmail)
def log_sent_email_save(sender, instance, created, **kwargs):
    if created:
        print(f"DEBUG: Signal 'post_save' for SentEmail (ID: {instance.pk})")
        # Assuming `employee` on SentEmail is who sent it
        identifier = instance.employee.name if instance.employee else "System/Unknown"
        log_audit_action(identifier, f"sent email to {instance.recipient_email} with subject '{instance.subject}' (ID: {instance.pk})")