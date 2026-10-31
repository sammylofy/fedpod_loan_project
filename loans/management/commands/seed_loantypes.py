from django.core.management.base import BaseCommand
from loans.models import LoanType

class Command(BaseCommand):
    help = 'Seeds the database with initial FEDPOD Cooperative Loan Types'

    def handle(self, *args, **kwargs):
        initial_loans = [
            {'name': 'Personal', 'interest_rate': 10.0, 'max_amount': 500000, 'max_duration_months': 12},
            {'name': 'Gold', 'interest_rate': 8.0, 'max_amount': 1000000, 'max_duration_months': 18},
            {'name': 'Home', 'interest_rate': 6.5, 'max_amount': 5000000, 'max_duration_months': 60},
            {'name': 'Vehicle', 'interest_rate': 9.0, 'max_amount': 3000000, 'max_duration_months': 36},
            {'name': 'Business', 'interest_rate': 12.0, 'max_amount': 2500000, 'max_duration_months': 24},
        ]

        for item in initial_loans:
            obj, created = LoanType.objects.update_or_create(
                name=item['name'],
                defaults={
                    'interest_rate': item['interest_rate'],
                    'max_amount': item['max_amount'],
                    'max_duration_months': item['max_duration_months'],
                }
            )
            action = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"{action} LoanType: {obj.name} ({obj.interest_rate}% p.a.)"))

        self.stdout.write(self.style.SUCCESS("Successfully seeded all 5 FEDPOD Cooperative Loan Types!"))