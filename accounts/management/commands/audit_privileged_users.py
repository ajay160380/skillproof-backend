from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'List any non-staff users whose role is admin, superadmin, manager, or auditor.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--demote',
            action='store_true',
            help='Demote flagged users to candidate role automatically.',
        )

    def handle(self, *args, **options):
        privileged_roles = ['admin', 'superadmin', 'manager', 'auditor']
        flagged_users = User.objects.filter(
            role__in=privileged_roles,
            is_staff=False,
            is_superuser=False
        ).order_by('-date_joined')

        count = flagged_users.count()
        if not count:
            self.stdout.write(self.style.SUCCESS("✓ No suspicious non-staff privileged user accounts found."))
            return

        self.stdout.write(self.style.WARNING(f"\n⚠️  Found {count} non-staff user(s) with privileged roles:\n"))
        self.stdout.write("-" * 90)
        self.stdout.write(f"{'ID':<6} {'Username':<22} {'Email':<30} {'Role':<14} {'Created At'}")
        self.stdout.write("-" * 90)
        for u in flagged_users:
            created_str = u.date_joined.strftime('%Y-%m-%d %H:%M') if u.date_joined else 'N/A'
            self.stdout.write(f"{u.id:<6} {u.username:<22} {u.email:<30} {u.role:<14} {created_str}")
        self.stdout.write("-" * 90)

        if options.get('demote'):
            updated = flagged_users.update(role='candidate')
            self.stdout.write(self.style.SUCCESS(f"\n✓ Demoted {updated} user(s) to candidate role."))
        else:
            self.stdout.write(self.style.NOTICE("\nRun with --demote to reset their roles to 'candidate'."))

