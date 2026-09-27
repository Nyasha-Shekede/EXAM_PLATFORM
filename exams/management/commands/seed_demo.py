from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from exams.models import Module,Category,Question,Option,Exam,Assignment
class Command(BaseCommand):
    help="Create a clearly labelled local demonstration dataset"
    def handle(self,*args,**opts):
        U=get_user_model(); admin,_=U.objects.get_or_create(username="admin",defaults={"email":"admin@example.test","is_staff":True,"is_superuser":True}); admin.is_staff=True; admin.is_superuser=True; admin.set_password("ChangeMe-Admin-2026"); admin.save()
        candidate,_=U.objects.get_or_create(username="DEMO001",defaults={"email":"candidate@example.test","first_name":"Demo","last_name":"Candidate"}); candidate.set_password("ChangeMe-Candidate-2026"); candidate.save()
        module,_=Module.objects.get_or_create(code="DEMO",defaults={"title":"Demonstration Module"}); cat,_=Category.objects.get_or_create(module=module,code="GENERAL",defaults={"title":"General knowledge"})
        rows=[("DEMO-001","Which control changes a multirotor's heading?",["Yaw","Pitch","Roll","Throttle"],"A","SINGLE"),("DEMO-002","Which items belong in a pre-flight check?",["Propeller condition","Battery security","Weather assessment","Airframe paint colour"],"A,B,C","MULTIPLE"),("DEMO-003","What should happen before an operational flight?",["Complete the approved planning process","Skip site assessment","Ignore weather","Use an uncharged battery"],"A","SINGLE")]
        for code,stem,options,correct,qtype in rows:
            q,_=Question.objects.update_or_create(code=code,defaults={"module":module,"category":cat,"stem":stem,"question_type":qtype,"status":"PUBLISHED","created_by":admin}); q.options.all().delete()
            for i,text in enumerate(options): Option.objects.create(question=q,key=chr(65+i),text=text,is_correct=chr(65+i) in correct.split(","))
        minimum_score=75
        exam,_=Exam.objects.update_or_create(code="DEMO-EXAM",defaults={"title":"Demonstration Examination","module":module,"duration_minutes":15,"question_count":3,"pass_mark":minimum_score,"max_attempts":3,"status":"PUBLISHED","show_answers_after":True})
        Assignment.objects.get_or_create(exam=exam,candidate=candidate)
        self.stdout.write(self.style.SUCCESS("Demo ready. admin / ChangeMe-Admin-2026; DEMO001 / ChangeMe-Candidate-2026. Change both passwords immediately."))
