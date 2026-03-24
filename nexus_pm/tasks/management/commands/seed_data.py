"""
Management command to seed the database with initial demo data.
Run: python manage.py seed_data
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
import random

from accounts.models import User
from tasks.models import Project, Task, BugReport, CalendarEvent, Notification


class Command(BaseCommand):
    help = 'Seed the database with demo data for IIAP PM'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Seeding database...'))

        # ── CREATE USERS ──────────────────────────────────────────────────────
        users_data = [
            {
                'username': 'admin',
                'password': 'admin123',
                'first_name': 'Alex',
                'last_name': 'Chen',
                'email': 'admin@IIAPpm.io',
                'role': 'admin',
                'team': 'general',
                'designation': 'System Administrator',
                'avatar_color': '#ef4444',
                'is_staff': True,
                'is_superuser': True,
            },
            {
                'username': 'pm_raj',
                'password': 'pass123',
                'first_name': 'Rajesh',
                'last_name': 'Kumar',
                'email': 'raj@IIAPpm.io',
                'role': 'project_manager',
                'team': 'electronics',
                'designation': 'Electronics Project Manager',
                'avatar_color': '#4f8ef7',
            },
            {
                'username': 'pm_sara',
                'password': 'pass123',
                'first_name': 'Sara',
                'last_name': 'Nair',
                'email': 'sara@IIAPpm.io',
                'role': 'project_manager',
                'team': 'software',
                'designation': 'Software Project Manager',
                'avatar_color': '#a855f7',
            },
            {
                'username': 'arjun_elec',
                'password': 'pass123',
                'first_name': 'Arjun',
                'last_name': 'Sharma',
                'email': 'arjun@IIAPpm.io',
                'role': 'member',
                'team': 'electronics',
                'designation': 'Electronics Engineer',
                'avatar_color': '#06b6d4',
            },
            {
                'username': 'priya_sw',
                'password': 'pass123',
                'first_name': 'Priya',
                'last_name': 'Menon',
                'email': 'priya@IIAPpm.io',
                'role': 'member',
                'team': 'software',
                'designation': 'Software Engineer',
                'avatar_color': '#22c55e',
            },
            {
                'username': 'vikram_mech',
                'password': 'pass123',
                'first_name': 'Vikram',
                'last_name': 'Pillai',
                'email': 'vikram@IIAPpm.io',
                'role': 'member',
                'team': 'mechanical',
                'designation': 'Mechanical Engineer',
                'avatar_color': '#f59e0b',
            },
            {
                'username': 'ananya_opt',
                'password': 'pass123',
                'first_name': 'Ananya',
                'last_name': 'Reddy',
                'email': 'ananya@IIAPpm.io',
                'role': 'member',
                'team': 'optics',
                'designation': 'Optics Engineer',
                'avatar_color': '#ec4899',
            },
            {
                'username': 'suresh_sim',
                'password': 'pass123',
                'first_name': 'Suresh',
                'last_name': 'Babu',
                'email': 'suresh@IIAPpm.io',
                'role': 'member',
                'team': 'simulation',
                'designation': 'Simulation Engineer',
                'avatar_color': '#8b5cf6',
            },
        ]

        created_users = {}
        for ud in users_data:
            password = ud.pop('password')
            is_staff = ud.pop('is_staff', False)
            is_superuser = ud.pop('is_superuser', False)
            user, created = User.objects.get_or_create(username=ud['username'], defaults=ud)
            if created:
                user.set_password(password)
                user.is_staff = is_staff
                user.is_superuser = is_superuser
                user.save()
                self.stdout.write(f'  Created user: {user.username}')
            created_users[user.username] = user

        admin = created_users['admin']
        pm_raj = created_users['pm_raj']
        pm_sara = created_users['pm_sara']
        arjun = created_users['arjun_elec']
        priya = created_users['priya_sw']
        vikram = created_users['vikram_mech']
        ananya = created_users['ananya_opt']
        suresh = created_users['suresh_sim']

        # ── CREATE PROJECTS ───────────────────────────────────────────────────
        today = date.today()
        projects_data = [
            {
                'name': 'PCB Design v2.0',
                'description': 'Redesign of the main control board with improved power management and reduced form factor.',
                'module': 'electronics',
                'status': 'active',
                'priority': 'high',
                'start_date': today - timedelta(days=30),
                'end_date': today + timedelta(days=60),
                'created_by': admin,
                'manager': pm_raj,
                'members_list': [arjun, pm_raj, admin],
            },
            {
                'name': 'Firmware OTA Update System',
                'description': 'Implement over-the-air firmware update capability with rollback support.',
                'module': 'software',
                'status': 'active',
                'priority': 'critical',
                'start_date': today - timedelta(days=15),
                'end_date': today + timedelta(days=45),
                'created_by': admin,
                'manager': pm_sara,
                'members_list': [priya, pm_sara, arjun],
            },
            {
                'name': 'Enclosure Thermal Analysis',
                'description': 'Mechanical analysis of heat dissipation in the device enclosure.',
                'module': 'mechanical',
                'status': 'planning',
                'priority': 'medium',
                'start_date': today + timedelta(days=5),
                'end_date': today + timedelta(days=90),
                'created_by': admin,
                'manager': pm_raj,
                'members_list': [vikram, pm_raj],
            },
            {
                'name': 'Optical Alignment Module',
                'description': 'Precision optical alignment system for laser positioning.',
                'module': 'optics',
                'status': 'active',
                'priority': 'high',
                'start_date': today - timedelta(days=20),
                'end_date': today + timedelta(days=40),
                'created_by': admin,
                'manager': pm_raj,
                'members_list': [ananya, pm_raj, suresh],
            },
            {
                'name': 'System Simulation Framework',
                'description': 'Build a comprehensive simulation environment for full-system testing.',
                'module': 'simulation',
                'status': 'active',
                'priority': 'medium',
                'start_date': today - timedelta(days=10),
                'end_date': today + timedelta(days=80),
                'created_by': admin,
                'manager': pm_sara,
                'members_list': [suresh, pm_sara, priya],
            },
        ]

        created_projects = {}
        for pd in projects_data:
            members_list = pd.pop('members_list')
            project, created = Project.objects.get_or_create(name=pd['name'], defaults=pd)
            if created:
                project.members.set(members_list)
                self.stdout.write(f'  Created project: {project.name}')
            created_projects[project.name] = project

        # ── CREATE TASKS ──────────────────────────────────────────────────────
        pcb = created_projects['PCB Design v2.0']
        fw = created_projects['Firmware OTA Update System']
        mech = created_projects['Enclosure Thermal Analysis']
        opt = created_projects['Optical Alignment Module']
        sim = created_projects['System Simulation Framework']

        tasks_data = [
            # PCB Project
            {'title': 'Schematic review for power supply section', 'project': pcb, 'status': 'done', 'priority': 'high', 'task_type': 'task', 'assigned_to': arjun, 'created_by': pm_raj, 'due_date': today - timedelta(days=10), 'estimated_hours': 4},
            {'title': 'Component selection for MCU', 'project': pcb, 'status': 'done', 'priority': 'high', 'task_type': 'task', 'assigned_to': arjun, 'created_by': pm_raj, 'due_date': today - timedelta(days=5), 'estimated_hours': 6},
            {'title': 'PCB layout - layer stackup definition', 'project': pcb, 'status': 'in_progress', 'priority': 'critical', 'task_type': 'task', 'assigned_to': arjun, 'created_by': pm_raj, 'due_date': today + timedelta(days=7), 'estimated_hours': 12},
            {'title': 'EMC compliance checklist', 'project': pcb, 'status': 'todo', 'priority': 'medium', 'task_type': 'task', 'assigned_to': pm_raj, 'created_by': admin, 'due_date': today + timedelta(days=20), 'estimated_hours': 3},
            {'title': 'Prototype board ordering', 'project': pcb, 'status': 'todo', 'priority': 'high', 'task_type': 'task', 'assigned_to': arjun, 'created_by': pm_raj, 'due_date': today + timedelta(days=15), 'estimated_hours': 2},
            {'title': 'Voltage regulator output noise fix', 'project': pcb, 'status': 'in_progress', 'priority': 'critical', 'task_type': 'bug', 'assigned_to': arjun, 'created_by': arjun, 'due_date': today + timedelta(days=3), 'estimated_hours': 8, 'tags': 'power,analog,urgent'},

            # Firmware Project
            {'title': 'Define OTA update protocol spec', 'project': fw, 'status': 'done', 'priority': 'high', 'task_type': 'task', 'assigned_to': priya, 'created_by': pm_sara, 'due_date': today - timedelta(days=8), 'estimated_hours': 5},
            {'title': 'Implement HTTPS download handler', 'project': fw, 'status': 'in_progress', 'priority': 'critical', 'task_type': 'feature', 'assigned_to': priya, 'created_by': pm_sara, 'due_date': today + timedelta(days=10), 'estimated_hours': 20, 'tags': 'networking,security'},
            {'title': 'Flash write & verify routine', 'project': fw, 'status': 'todo', 'priority': 'critical', 'task_type': 'feature', 'assigned_to': priya, 'created_by': pm_sara, 'due_date': today + timedelta(days=18), 'estimated_hours': 15},
            {'title': 'Rollback mechanism on failed update', 'project': fw, 'status': 'todo', 'priority': 'high', 'task_type': 'feature', 'assigned_to': arjun, 'created_by': pm_sara, 'due_date': today + timedelta(days=25), 'estimated_hours': 10},
            {'title': 'Unit tests for OTA module', 'project': fw, 'status': 'todo', 'priority': 'medium', 'task_type': 'task', 'assigned_to': priya, 'created_by': pm_sara, 'due_date': today + timedelta(days=35), 'estimated_hours': 8},
            {'title': 'Memory overflow on large firmware chunks', 'project': fw, 'status': 'in_progress', 'priority': 'critical', 'task_type': 'bug', 'assigned_to': priya, 'created_by': priya, 'due_date': today + timedelta(days=2), 'estimated_hours': 6, 'tags': 'memory,critical'},

            # Mechanical Project
            {'title': 'CAD model of enclosure v1', 'project': mech, 'status': 'todo', 'priority': 'high', 'task_type': 'task', 'assigned_to': vikram, 'created_by': pm_raj, 'due_date': today + timedelta(days=14)},
            {'title': 'Material selection for housing', 'project': mech, 'status': 'todo', 'priority': 'medium', 'task_type': 'research', 'assigned_to': vikram, 'created_by': pm_raj, 'due_date': today + timedelta(days=20)},

            # Optics Project
            {'title': 'Laser beam collimation design', 'project': opt, 'status': 'done', 'priority': 'high', 'task_type': 'task', 'assigned_to': ananya, 'created_by': pm_raj, 'due_date': today - timedelta(days=5)},
            {'title': 'Mount assembly tolerancing', 'project': opt, 'status': 'in_progress', 'priority': 'high', 'task_type': 'task', 'assigned_to': ananya, 'created_by': pm_raj, 'due_date': today + timedelta(days=8)},
            {'title': 'Detector sensitivity calibration', 'project': opt, 'status': 'review', 'priority': 'medium', 'task_type': 'task', 'assigned_to': suresh, 'created_by': pm_raj, 'due_date': today + timedelta(days=12)},

            # Simulation Project
            {'title': 'Set up simulation environment', 'project': sim, 'status': 'done', 'priority': 'high', 'task_type': 'task', 'assigned_to': suresh, 'created_by': pm_sara, 'due_date': today - timedelta(days=3)},
            {'title': 'Model thermal behaviour of PCB', 'project': sim, 'status': 'in_progress', 'priority': 'medium', 'task_type': 'task', 'assigned_to': suresh, 'created_by': pm_sara, 'due_date': today + timedelta(days=15)},
            {'title': 'Integrate hardware-in-loop testing', 'project': sim, 'status': 'todo', 'priority': 'high', 'task_type': 'feature', 'assigned_to': priya, 'created_by': pm_sara, 'due_date': today + timedelta(days=40)},
        ]

        for td in tasks_data:
            if not Task.objects.filter(title=td['title'], project=td['project']).exists():
                Task.objects.create(**td)
                self.stdout.write(f'  Created task: {td["title"][:50]}')

        # Update project progress
        for p in Project.objects.all():
            p.update_progress()

        # ── CREATE BUG REPORTS ────────────────────────────────────────────────
        bugs_data = [
            {
                'title': 'ADC readings drift at high temperature',
                'project': pcb,
                'reported_by': arjun,
                'assigned_to': arjun,
                'severity': 'high',
                'status': 'open',
                'description': 'ADC readings show 3-5% drift when PCB temperature exceeds 70°C.',
                'steps_to_reproduce': '1. Heat PCB to 70°C\n2. Measure ADC output\n3. Compare to room-temp baseline',
                'expected_behavior': 'Readings stable within 0.5% across temperature range.',
                'actual_behavior': 'Drift of 3-5% observed above 70°C.',
            },
            {
                'title': 'OTA update fails on poor network connection',
                'project': fw,
                'reported_by': priya,
                'assigned_to': priya,
                'severity': 'critical',
                'status': 'in_progress',
                'description': 'When network quality drops mid-download, the update process hangs indefinitely.',
                'steps_to_reproduce': '1. Start OTA update\n2. Reduce network bandwidth to <10kbps\n3. Observe hang',
                'expected_behavior': 'Download should timeout and retry gracefully.',
                'actual_behavior': 'Process hangs indefinitely, requiring manual reboot.',
            },
        ]
        for bd in bugs_data:
            if not BugReport.objects.filter(title=bd['title']).exists():
                BugReport.objects.create(**bd)
                self.stdout.write(f'  Created bug: {bd["title"][:50]}')

        # ── CREATE CALENDAR EVENTS ────────────────────────────────────────────
        events_data = [
            {
                'title': 'PCB Design Review',
                'event_type': 'review',
                'project': pcb,
                'start_datetime': timezone.now() + timedelta(days=3, hours=10),
                'end_datetime': timezone.now() + timedelta(days=3, hours=12),
                'created_by': pm_raj,
                'color': '#4f8ef7',
                'description': 'Full schematic and layout review with the team.',
            },
            {
                'title': 'OTA Firmware Milestone',
                'event_type': 'milestone',
                'project': fw,
                'start_datetime': timezone.now() + timedelta(days=10, hours=9),
                'end_datetime': timezone.now() + timedelta(days=10, hours=10),
                'created_by': pm_sara,
                'color': '#22c55e',
                'description': 'First working OTA update demo.',
            },
            {
                'title': 'Sprint Planning Meeting',
                'event_type': 'meeting',
                'start_datetime': timezone.now() + timedelta(days=1, hours=9),
                'end_datetime': timezone.now() + timedelta(days=1, hours=10),
                'created_by': admin,
                'color': '#f59e0b',
                'description': 'Bi-weekly sprint planning for all teams.',
            },
        ]
        for ed in events_data:
            if not CalendarEvent.objects.filter(title=ed['title']).exists():
                attendees = ed.pop('attendees', [])
                event = CalendarEvent.objects.create(**ed)
                if attendees:
                    event.attendees.set(attendees)
                self.stdout.write(f'  Created event: {ed["title"]}')

        # ── CREATE NOTIFICATIONS ──────────────────────────────────────────────
        notifs = [
            {
                'recipient': arjun,
                'sender': pm_raj,
                'notification_type': 'task_assigned',
                'title': 'New task assigned: PCB layout',
                'message': 'Rajesh Kumar assigned you a critical task for PCB Design v2.0.',
                'is_read': False,
            },
            {
                'recipient': priya,
                'sender': pm_sara,
                'notification_type': 'task_assigned',
                'title': 'New task assigned: OTA download handler',
                'message': 'Sara Nair assigned you a feature task in Firmware OTA Update System.',
                'is_read': False,
            },
        ]
        for nd in notifs:
            Notification.objects.get_or_create(
                recipient=nd['recipient'],
                title=nd['title'],
                defaults=nd
            )

        self.stdout.write(self.style.SUCCESS('\n✅ Database seeded successfully!\n'))
        self.stdout.write(self.style.SUCCESS('Login credentials:'))
        self.stdout.write('  Admin:          admin / admin123')
        self.stdout.write('  Project Manager: pm_raj / pass123')
        self.stdout.write('  Project Manager: pm_sara / pass123')
        self.stdout.write('  Member:         arjun_elec / pass123')
        self.stdout.write('  Member:         priya_sw / pass123')
        self.stdout.write('  Member:         vikram_mech / pass123')
        self.stdout.write('')
