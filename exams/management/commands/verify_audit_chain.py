from django.core.management.base import BaseCommand,CommandError
from exams.services import verify_audit_chain
class Command(BaseCommand):
    help="Verify linkage of the append-only application audit chain"
    def handle(self,*args,**opts):
        ok,event=verify_audit_chain()
        if not ok: raise CommandError(f"Audit chain link failed at event {event}")
        self.stdout.write(self.style.SUCCESS("Audit chain links verified."))
