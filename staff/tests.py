from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import date, time
from .models import emp_registers, Project, Task, Timesheet, Member, StatusMaster, PriorityMaster, RateStatusMaster

class ProjectModelTest(TestCase):
    def setUp(self):
        self.emp = emp_registers.objects.create(name="Test Employee", email="test@example.com", password="pass1234")
        self.status = StatusMaster.objects.create(status="Pending")
        self.rate_status = RateStatusMaster.objects.create(status="Normal")
        self.priority = PriorityMaster.objects.create(level=1, label="High")
        self.project = Project.objects.create(
            emp_id=self.emp,
            pname="Test Project",
            start_date=date.today(),
            status=self.status,
            rate_status=self.rate_status,
            priority=self.priority,
            admin="Admin",
            manager="Manager",
            client="Client"
        )

    def test_project_creation(self):
        self.assertEqual(self.project.pname, "Test Project")
        self.assertEqual(self.project.status.status, "Pending")
        self.assertEqual(self.project.admin, "Admin")

class TaskModelTest(TestCase):
    def setUp(self):
        self.emp = emp_registers.objects.create(name="Test Employee", email="test2@example.com", password="pass1234")
        self.status = StatusMaster.objects.create(status="Pending")
        self.priority = PriorityMaster.objects.create(level=1, label="High")
        self.project = Project.objects.create(
            emp_id=self.emp,
            pname="Test Project",
            start_date=date.today(),
            status=self.status,
            admin="Admin",
            manager="Manager",
            client="Client"
        )
        self.member = Member.objects.create(emp_id=self.emp, name="Member1", email="member1@example.com")
        self.task = Task.objects.create(
            emp_id=self.emp,
            project=self.project,
            title="Test Task",
            description="Task description",
            status=self.status,
            priority=self.priority,
            leader="Leader"
        )
        self.task.assigned_to.add(self.member)

    def test_task_creation(self):
        self.assertEqual(self.task.title, "Test Task")
        self.assertEqual(self.task.project.pname, "Test Project")
        self.assertIn(self.member, self.task.assigned_to.all())

class TimesheetModelTest(TestCase):
    def setUp(self):
        self.emp = emp_registers.objects.create(name="Test Employee", email="test3@example.com", password="pass1234")
        self.project = Project.objects.create(
            emp_id=self.emp,
            pname="Test Project",
            start_date=date.today(),
            admin="Admin",
            manager="Manager",
            client="Client"
        )
        self.timesheet = Timesheet.objects.create(
            emp_id=self.emp,
            pname=self.project,
            task="Test Task",
            date=date.today(),
            start_time=time(9, 0),
            end_time=time(17, 0),
            description="Worked on testing",
            attachment=None
        )

    def test_timesheet_creation(self):
        self.assertEqual(self.timesheet.task, "Test Task")
        self.assertEqual(self.timesheet.pname.pname, "Test Project")
        self.assertEqual(self.timesheet.emp_id.name, "Test Employee")

class ProjectViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.emp = emp_registers.objects.create(name="Test Employee", email="test4@example.com", password="pass1234")
        self.status = StatusMaster.objects.create(status="Pending")
        self.rate_status = RateStatusMaster.objects.create(status="Normal")
        self.priority = PriorityMaster.objects.create(level=1, label="High")
        self.project = Project.objects.create(
            emp_id=self.emp,
            pname="Test Project",
            start_date=date.today(),
            status=self.status,
            rate_status=self.rate_status,
            priority=self.priority,
            admin="Admin",
            manager="Manager",
            client="Client"
        )
        session = self.client.session
        session['user_id'] = self.emp.id
        session.save()

    def test_project_list_view(self):
        url = reverse('project', kwargs={'user_id': self.emp.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Project")

    def test_add_project_view_get(self):
        url = reverse('add_project', kwargs={'user_id': self.emp.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

class TaskViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.emp = emp_registers.objects.create(name="Test Employee", email="test5@example.com", password="pass1234")
        self.status = StatusMaster.objects.create(status="Pending")
        self.priority = PriorityMaster.objects.create(level=1, label="High")
        self.project = Project.objects.create(
            emp_id=self.emp,
            pname="Test Project",
            start_date=date.today(),
            status=self.status,
            admin="Admin",
            manager="Manager",
            client="Client"
        )
        self.member = Member.objects.create(emp_id=self.emp, name="Member1", email="member1@example.com")
        self.task = Task.objects.create(
            emp_id=self.emp,
            project=self.project,
            title="Test Task",
            description="Task description",
            status=self.status,
            priority=self.priority,
            leader="Leader"
        )
        self.task.assigned_to.add(self.member)
        session = self.client.session
        session['user_id'] = self.emp.id
        session.save()

    def test_task_list_view(self):
        url = reverse('task_list_view', kwargs={'user_id': self.emp.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Task")

    def test_add_task_view_get(self):
        url = reverse('add_task', kwargs={'user_id': self.emp.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

class TimesheetViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.emp = emp_registers.objects.create(name="Test Employee", email="test6@example.com", password="pass1234")
        self.project = Project.objects.create(
            emp_id=self.emp,
            pname="Test Project",
            start_date=date.today(),
            admin="Admin",
            manager="Manager",
            client="Client"
        )
        self.timesheet = Timesheet.objects.create(
            emp_id=self.emp,
            pname=self.project,
            task="Test Task",
            date=date.today(),
            start_time=time(9, 0),
            end_time=time(17, 0),
            description="Worked on testing",
            attachment=None
        )
        session = self.client.session
        session['user_id'] = self.emp.id
        session.save()

    def test_user_timesheet_view(self):
        url = reverse('user_timesheet')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Task")

    def test_update_timesheet_view_get(self):
        url = reverse('update_timesheet', kwargs={'user_id': self.emp.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

class ApiTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.emp = emp_registers.objects.create(name="Test Employee", email="test7@example.com", password="pass1234")
        self.status = StatusMaster.objects.create(status="Pending")
        self.project = Project.objects.create(
            emp_id=self.emp,
            pname="Test Project",
            start_date=date.today(),
            status=self.status,
            admin="Admin",
            manager="Manager",
            client="Client"
        )
        self.task = Task.objects.create(
            emp_id=self.emp,
            project=self.project,
            title="Test Task",
            description="Task description",
            status=self.status,
            leader="Leader"
        )
        self.task.assigned_to.add(Member.objects.create(emp_id=self.emp, name="Member1", email="member1@example.com"))
        session = self.client.session
        session['user_id'] = self.emp.id
        session.save()

    def test_get_tasks_api(self):
        url = reverse('get_tasks')
        response = self.client.get(url, {'project_id': self.project.id, 'user_id': self.emp.id})
        self.assertEqual(response.status_code, 200)
        self.assertIn('tasks', response.json())

    def test_get_project_members_api(self):
        url = reverse('get_project_members', kwargs={'project_id': self.project.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)
