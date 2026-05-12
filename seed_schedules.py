import os
import django
import random
from datetime import timedelta, time
from django.utils import timezone

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangosimplemission.settings')
django.setup()

from djangosimplemissionapp.models import Schedule, User, Role

def seed_schedules(n=100):
    users = list(User.objects.all())
    roles = list(Role.objects.all())

    if not users:
        print("No users found. Please create some users first.")
        return

    task_titles = [
        "Follow up with client", "Demo presentation", "Internal review", 
        "Product walkthrough", "Project kickoff", "Strategy meeting",
        "Weekly sync", "Quality check", "Onboarding session", "Client feedback call",
        "Database maintenance", "Frontend bug fix", "API integration",
        "UI/UX review", "Marketing brainstorm", "Lead nurturing",
        "Contract signing", "Server migration", "Budget approval", "Team building"
    ]

    descriptions = [
        "Discuss the latest updates and gather feedback.",
        "Present the new features to the stakeholder.",
        "Review progress and identify bottlenecks.",
        "Introduce the system to the new client team.",
        "Plan the next phase of the project.",
        "Analyze the current performance metrics.",
        "Coordinate tasks for the upcoming week.",
        "Ensure all deliverables meet the standards.",
        "Help the new hire get started with the tools.",
        "Listen to client concerns and document requirements.",
        "Optimize the performance of the main database.",
        "Fix the reported issues in the login flow.",
        "Connect the new payment gateway to the system.",
        "Go over the mockups for the new dashboard.",
        "Prepare the content for the next campaign.",
        "Send personalized emails to potential leads.",
        "Finalize the terms of the new agreement.",
        "Move the data to the new production server.",
        "Review and approve the department budget.",
        "A short session to boost team morale."
    ]

    schedules_created = 0
    today = timezone.now().date()

    for i in range(n):
        # 70% chance to assign to a user, 30% chance to assign to a role
        assign_to_user = random.random() < 0.7
        
        assigned_to = random.choice(users) if assign_to_user else None
        assigned_role = random.choice(roles) if (not assign_to_user and roles) else None
        
        # If no role assigned but we wanted to, fallback to user
        if not assigned_to and not assigned_role:
            assigned_to = random.choice(users)

        created_by = random.choice(users)
        
        # Random date between -15 and +45 days
        random_days = random.randint(-15, 45)
        schedule_date = today + timedelta(days=random_days)
        
        # Random time
        schedule_time = time(random.randint(9, 18), random.choice([0, 15, 30, 45]))

        schedule = Schedule.objects.create(
            title=f"{random.choice(task_titles)} #{i+1}",
            description=random.choice(descriptions),
            schedule_date=schedule_date,
            schedule_time=schedule_time,
            assigned_to=assigned_to,
            assigned_role=assigned_role,
            created_by=created_by,
            is_completed=random.choice([True, False]) if schedule_date < today else False
        )
        schedules_created += 1

    print(f"Successfully created {schedules_created} demo schedule entries.")

if __name__ == "__main__":
    seed_schedules(100)
