from django.core.management.base import BaseCommand
from staff.models import emp_registers, Holiday, LeaveRecord, LatestPayslip
from datetime import date, timedelta
import csv
import os

class Command(BaseCommand):
    help = "Generate payslips for all employees at month end."

    def handle(self, *args, **kwargs):
        today = date.today()
        year, month = today.year, today.month
        filename = f"payslip_{year}_{month}.csv"
        filepath = os.path.join("media", filename)

        holidays = Holiday.objects.filter(date__year=year, date__month=month).values_list('date', flat=True)
        working_days = [date(year, month, day) for day in range(1, 32)
                        if date(year, month, day).weekday() < 5 and day <= 28]

        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "emp_id", "Employee_Name", "Employee_Email", "SALARY BASIC", "SALARY_HRA", "SALARY_DA", "TOTAL_SALARY",
                "Present Days", "Paid Leaves", "Weekly Off", "Unpaid Leaves", "Festivals", "Total Paid Days",
                "GROSS BASIC", "GROSS HRA", "GROSS DA", "CONVENCE ALLOWNCES", "SPECIAL ALLOWNCES",
                "Project Incentive", "Variable Pay", "GROSS TOTAL", "ESI", "PF", "Salary Advance", "Negative Leave",
                "TDS", "Total Deductions", "NET SALARY", "Month"
            ])

            for emp in emp_registers.objects.all():
                basic = float(emp.salary or 0)
                hra = basic * 0.4
                da = basic * 0.1
                total_basic = basic  # Normally should calculate based on attendance
                gross = basic + hra + da + 1600 + 2000

                esi = gross * 0.0075
                pf = gross * 0.12
                tds = gross * 0.05
                deductions = esi + pf + tds
                net = gross - deductions

                writer.writerow([
                    emp.id, emp.name, emp.email, basic, hra, da, basic + hra + da,
                    22, 2, 8, 0, len(holidays), 24,
                    basic, hra, da, 1600, 2000, 0, 0,
                    gross, esi, pf, 0, 0, tds,
                    deductions, net, f"{today.strftime('%B %Y')}"
                ])

        # Store filename in LatestPayslip model
        LatestPayslip.objects.all().delete()
        LatestPayslip.objects.create(file_name=filename)

        self.stdout.write(self.style.SUCCESS(f"Payslip generated: {filename}"))
