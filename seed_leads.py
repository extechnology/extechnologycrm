import os
import django
import random
from datetime import timedelta
from django.utils import timezone

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangosimplemission.settings')
django.setup()

from djangosimplemissionapp.models import Lead, User, FollowUp

def seed_leads(n=100):
    users = list(User.objects.all())
    if not users:
        print("No users found. Please create some users first.")
        return

    company_names = [
        "TechNova", "GreenScape", "Oceanic Solutions", "Apex Dynamics", "Stellar Systems",
        "Velocity Labs", "Crystal Clear", "Quantum Quest", "Horizon Hub", "Summit Services",
        "NexGen IT", "Blue River", "Silver Lining", "Golden Gate", "Pinnacle Partners",
        "Everest Enterprises", "Fusion Forge", "Echo Edge", "Unity Utilities", "Pulse Platforms",
        "Vanguard Ventures", "Zenith Zone", "Omni Options", "Legacy Logistics", "Infinite Innovations",
        "Global Grid", "Smart Shield", "Rapid Reach", "Agile Assets", "Bright Beam",
        "Cloud Craft", "Data Dream", "Ether Entry", "Flux Flow", "Glow Grow",
        "Hyper Hive", "Icon Ink", "Jolt Joy", "Kite Key", "Lift Life",
        "Mega Mind", "Nova Nest", "Orbit Optic", "Prime Path", "Quick Quest",
        "Rise Real", "Solar Sky", "Terra Trace", "Ultra Unit", "Vision Vibe"
    ]

    names = ["Alice", "Bob", "Charlie", "David", "Eve", "Frank", "Grace", "Heidi", "Ivan", "Judy", "Mallory", "Nia", "Oscar", "Peggy", "Quentin", "Rose", "Sybil", "Trent", "Uma", "Victor"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]

    interest_levels = ['warm', 'hot', 'cold']
    conversion_statuses = ['new', 'contacted', 'proposal_sent', 'negotiation', 'closed', 'denied']
    sources = ['LinkedIn', 'Referral', 'Website', 'Social Media', 'Cold Call', 'Email Marketing']

    leads_created = 0
    for i in range(n):
        company = f"{random.choice(company_names)} {random.randint(1, 1000)}"
        first = random.choice(names)
        last = random.choice(last_names)
        person = f"{first} {last}"
        
        lead = Lead.objects.create(
            company_name=company,
            contact_person=person,
            contact_number=f"+91{random.randint(6000000000, 9999999999)}",
            email=f"{first.lower()}.{last.lower()}@example.com",
            website=f"www.{company.lower().replace(' ', '')}.com",
            address=f"{random.randint(1, 500)} Main St, City {random.randint(1, 20)}",
            lead_source=random.choice(sources),
            description=f"Automated demo lead for {company}. Client is looking for strategic growth and technical support.",
            assigned_to=random.choice(users)
        )

        FollowUp.objects.create(
            lead=lead,
            interest_level=random.choice(interest_levels),
            conversion_status=random.choice(conversion_statuses),
            followup_date=timezone.now().date() + timedelta(days=random.randint(1, 30)) if random.random() > 0.5 else None,
            note="Initial contact established. Interested in further discussion."
        )
        leads_created += 1

    print(f"Successfully created {leads_created} demo leads across {len(users)} users.")

if __name__ == "__main__":
    seed_leads(100)
