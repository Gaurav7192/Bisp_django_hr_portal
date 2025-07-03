import os
import datetime
import logging
from django.conf import settings

# Configure a dedicated logger for employee audits
employee_audit_logger = logging.getLogger('employee_audit')
employee_audit_logger.setLevel(logging.INFO) # Set to INFO, DEBUG, etc. as needed
employee_audit_logger.propagate = False # Prevent messages from going to default Django loggers

def get_employee_audit_filepath(employee_email):
    """
    Generates the path for an employee's daily audit log file.
    Logs will be stored in a subfolder like: audit_logs/john.doe_at_example_dot_com_YYYY-MM-DD_audit.log
    """
    # Define where audit logs should be stored. Reads from settings or defaults to 'audit_logs' in BASE_DIR.
    audit_log_dir = getattr(settings, 'AUDIT_LOG_DIR', os.path.join(settings.BASE_DIR, 'audit_logs'))
    os.makedirs(audit_log_dir, exist_ok=True) # Ensure this directory exists

    today_str = datetime.date.today().strftime('%Y-%m-%d')
    # Sanitize email for filename (replace characters that might cause issues in file names)
    safe_email = employee_email.replace('@', '_at_').replace('.', '_dot_')
    filename = f"{safe_email}_{today_str}_audit.log"
    return os.path.join(audit_log_dir, filename)

def log_employee_action(employee_email, action_description):
    """
    Logs an action to a specific employee's daily audit log file.
    This function dynamically attaches and detaches a file handler to ensure
    each log entry goes to the correct, employee-specific file.
    """
    if not employee_email:
        # Handle cases where employee_email might be empty or None
        logging.error("log_employee_action called with empty employee_email.")
        return

    log_filepath = get_employee_audit_filepath(employee_email)

    # Remove existing handlers from this logger to ensure only the new one is active
    for handler in list(employee_audit_logger.handlers):
        employee_audit_logger.removeHandler(handler)

    # Create a file handler for the specific employee's log file
    file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    file_handler.setFormatter(formatter)
    employee_audit_logger.addHandler(file_handler)

    # Log the action
    employee_audit_logger.info(action_description)

    # Remove the handler after logging to prevent it from accumulating or
    # writing subsequent logs to the wrong file if email changes
    employee_audit_logger.removeHandler(file_handler)
    file_handler.close() # Ensure the file handle is released

import os
import csv
from datetime import date, timedelta
from calendar import monthrange
from django.core.mail import EmailMessage
from django.conf import settings
from staff.models import emp_registers, LeaveRecord, Holiday, LatestPayslip
#
#
# def is_last_day_of_month():
#     today = date.today()
#     tomorrow = today + timedelta(days=1)
#     return tomorrow.day == 1
#
#
# def generate_salary_csv_and_send():
#     today = date.today()
#     year, month = today.year, today.month
#
#     filename = f"payslip_{year}_{month}.csv"
#     filepath = os.path.join("media", filename)
#
#     if os.path.exists(filepath):
#         return "Payslip already generated."
#
#     holidays = Holiday.objects.filter(date__year=year, date__month=month).values_list('date', flat=True)
#     total_days = monthrange(year, month)[1]
#
#     with open(filepath, "w", newline="") as f:
#         writer = csv.writer(f)
#         writer.writerow([
#             "emp_id", "Employee_Name", "Employee_Email", "SALARY BASIC", "SALARY_HRA", "SALARY_DA", "TOTAL_SALARY",
#             "Present Days", "Paid Leaves", "Weekly Off", "Unpaid Leaves", "Festivals", "Total Paid Days",
#             "GROSS BASIC", "GROSS HRA", "GROSS DA", "CONVENCE ALLOWNCES", "SPECIAL ALLOWNCES",
#             "Project Incentive", "Variable Pay", "GROSS TOTAL", "ESI", "PF", "Salary Advance", "Negative Leave",
#             "TDS", "Total Deductions", "NET SALARY", "Month"
#         ])
#
#         for emp in emp_registers.objects.all():
#             annual_ctc = float(emp.salary or 0)
#             monthly_ctc = annual_ctc / 12
#
#             # Split monthly CTC into components
#             basic = round(monthly_ctc * 0.40, 2)
#             hra = round(monthly_ctc * 0.20, 2)
#             da = round(monthly_ctc * 0.10, 2)
#             conveyance = 1600.00  # fixed
#             special = round(monthly_ctc - (basic + hra + da + conveyance), 2)
#             gross_monthly = basic + hra + da + conveyance + special
#
#             # Approved leaves this month
#             leaves = LeaveRecord.objects.filter(
#                 emp_id=emp,
#                 approval_status__id=1,  # Approved
#                 start_date__month=month,
#                 start_date__year=year
#             )
#
#             paid_leave_days = sum(l.no_of_days for l in leaves if l.leave_type and l.leave_type.payable)
#             unpaid_leave_days = sum(l.no_of_days for l in leaves if l.leave_type and not l.leave_type.payable)
#             weekly_offs = 4  # Assumption
#             holidays_count = len(holidays)
#
#             # Calculate paid/unpaid days
#             present_days = total_days - (weekly_offs + paid_leave_days + unpaid_leave_days)
#             total_paid_days = present_days + paid_leave_days + holidays_count
#
#             # Per-day gross salary
#             per_day_salary = gross_monthly / total_days
#             adjusted_salary = round(per_day_salary * total_paid_days, 2)
#
#             # Adjusted components based on actual paid days
#             gross_basic = round(basic / total_days * total_paid_days, 2)
#             gross_hra = round(hra / total_days * total_paid_days, 2)
#             gross_da = round(da / total_days * total_paid_days, 2)
#
#             gross_total = round(adjusted_salary, 2)
#
#             # Deductions
#             esi = round(gross_total * 0.0075, 2)
#             pf = round(gross_total * 0.12, 2)
#             tds = round(gross_total * 0.05, 2)
#             total_deductions = round(esi + pf + tds, 2)
#
#             net_salary = round(gross_total - total_deductions, 2)
#
#             # Write to CSV
#             writer.writerow([
#                 emp.id, emp.name, emp.email, basic, hra, da, round(basic + hra + da, 2),
#                 present_days, paid_leave_days, weekly_offs, unpaid_leave_days, holidays_count, total_paid_days,
#                 gross_basic, gross_hra, gross_da, conveyance, special,
#                 0, 0, gross_total, esi, pf, 0, 0, tds, total_deductions, net_salary,
#                 f"{today.strftime('%B %Y')}"
#             ])
#
#     # Store payslip info in DB
#     LatestPayslip.objects.all().delete()
#     LatestPayslip.objects.create(file_name=filename)
#
#     # Send Email to HR
#     email = EmailMessage(
#         subject=f"Payslip Generated - {today.strftime('%B %Y')}",
#         body="Attached is the auto-generated salary slip for the current month.",
#         from_email=settings.DEFAULT_FROM_EMAIL,
#         to=["hr@example.com"]  # Update as needed
#     )
#     email.attach_file(filepath)
#     email.send()
#
#     return "Payslip generated and emailed."
