import hashlib, secrets, uuid
import logging
logger=logging.getLogger(__name__)

def make_rejoin_token(): return secrets.token_urlsafe(18)
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone

class Module(models.Model):
    code=models.CharField(max_length=30,primary_key=True)
    title=models.CharField(max_length=150)
    default_pass_mark=models.DecimalField(max_digits=5,decimal_places=2,default=75,validators=[MinValueValidator(0),MaxValueValidator(100)])
    active=models.BooleanField(default=True)
    def __str__(self): return f"{self.code} — {self.title}"

class Category(models.Model):
    module=models.ForeignKey(Module,on_delete=models.PROTECT,related_name="categories")
    code=models.CharField(max_length=50)
    title=models.CharField(max_length=150)
    class Meta: constraints=[models.UniqueConstraint(fields=["module","code"],name="unique_category_module")]
    def __str__(self): return f"{self.module_id}/{self.code}"

class Question(models.Model):
    SINGLE="SINGLE"; MULTIPLE="MULTIPLE"
    TYPES=[(SINGLE,"Single choice"),(MULTIPLE,"Multiple choice")]
    DRAFT="DRAFT"; PUBLISHED="PUBLISHED"; RETIRED="RETIRED"
    STATUSES=[(DRAFT,"Draft"),(PUBLISHED,"Published"),(RETIRED,"Retired")]
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    code=models.CharField(max_length=60,unique=True)
    module=models.ForeignKey(Module,on_delete=models.PROTECT,related_name="questions")
    category=models.ForeignKey(Category,on_delete=models.PROTECT,related_name="questions")
    question_type=models.CharField(max_length=10,choices=TYPES,default=SINGLE)
    stem=models.TextField()
    explanation=models.TextField(blank=True)
    difficulty=models.CharField(max_length=10,choices=[("EASY","Easy"),("MEDIUM","Medium"),("HARD","Hard")],default="MEDIUM")
    marks=models.DecimalField(max_digits=6,decimal_places=2,default=1,validators=[MinValueValidator(0.01)])
    status=models.CharField(max_length=10,choices=STATUSES,default=DRAFT)
    version=models.PositiveIntegerField(default=1)
    image=models.ImageField(upload_to="question_images/%Y/%m/",blank=True,validators=[FileExtensionValidator(["jpg","jpeg","png","webp"])])
    image_alt_text=models.CharField(max_length=300,blank=True)
    image_sha256=models.CharField(max_length=64,blank=True,editable=False)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="questions_created",null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    def clean(self):
        super().clean()
        if self.category_id and self.module_id and self.category.module_id != self.module_id: raise ValidationError({"category":"Category must belong to the selected module."})
        if self.image and not self.image_alt_text.strip(): raise ValidationError({"image_alt_text":"Alt text is required for question images."})
    def save(self,*a,**kw):
        super().save(*a,**kw)
        if self.image:
            try:
                self.image.open("rb"); digest=hashlib.sha256(self.image.read()).hexdigest(); self.image.close()
                if digest != self.image_sha256: Question.objects.filter(pk=self.pk).update(image_sha256=digest); self.image_sha256=digest
            except (OSError, ValueError) as exc:
                logger.warning("Could not hash question image for %s: %s", self.pk, exc)
    def __str__(self): return f"{self.code}: {self.stem[:60]}"

class Option(models.Model):
    question=models.ForeignKey(Question,on_delete=models.CASCADE,related_name="options")
    key=models.CharField(max_length=2)
    text=models.TextField()
    is_correct=models.BooleanField(default=False)
    class Meta: ordering=["key"]; constraints=[models.UniqueConstraint(fields=["question","key"],name="unique_question_option")]
    def __str__(self): return f"{self.question.code} {self.key}"

class Exam(models.Model):
    DRAFT="DRAFT"; PUBLISHED="PUBLISHED"; CLOSED="CLOSED"
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    code=models.CharField(max_length=50,unique=True); title=models.CharField(max_length=180)
    module=models.ForeignKey(Module,on_delete=models.PROTECT,related_name="exams")
    instructions=models.TextField(blank=True)
    duration_minutes=models.PositiveIntegerField(default=30,validators=[MinValueValidator(1),MaxValueValidator(480)])
    question_count=models.PositiveIntegerField(default=20,validators=[MinValueValidator(1)])
    pass_mark=models.DecimalField(max_digits=5,decimal_places=2,default=75,validators=[MinValueValidator(0),MaxValueValidator(100)])
    max_attempts=models.PositiveIntegerField(default=1,validators=[MinValueValidator(1)])
    shuffle_questions=models.BooleanField(default=True); shuffle_options=models.BooleanField(default=True)
    available_from=models.DateTimeField(null=True,blank=True); available_until=models.DateTimeField(null=True,blank=True)
    show_answers_after=models.BooleanField(default=False)
    status=models.CharField(max_length=10,choices=[(DRAFT,"Draft"),(PUBLISHED,"Published"),(CLOSED,"Closed")],default=DRAFT)
    created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    def clean(self):
        if self.available_from and self.available_until and self.available_from >= self.available_until: raise ValidationError("Availability end must be after start.")
        if self.status==self.PUBLISHED and self.module_id:
            pool=Question.objects.filter(module_id=self.module_id,status=Question.PUBLISHED).count()
            if pool < self.question_count: raise ValidationError(f"Cannot publish: only {pool} published questions for a {self.question_count}-question exam.")
    def is_available(self,now=None):
        now=now or timezone.now(); return self.status==self.PUBLISHED and (not self.available_from or now>=self.available_from) and (not self.available_until or now<=self.available_until)
    def __str__(self): return f"{self.code} — {self.title}"

class Assignment(models.Model):
    exam=models.ForeignKey(Exam,on_delete=models.CASCADE,related_name="assignments")
    candidate=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="exam_assignments")
    assigned_at=models.DateTimeField(auto_now_add=True); extra_time_minutes=models.PositiveIntegerField(default=0); active=models.BooleanField(default=True)
    class Meta: constraints=[models.UniqueConstraint(fields=["exam","candidate"],name="unique_assignment")]
    def __str__(self): return f"{self.candidate} / {self.exam}"

class Attempt(models.Model):
    IN_PROGRESS="IN_PROGRESS"; SUBMITTED="SUBMITTED"; EXPIRED="EXPIRED"
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    exam=models.ForeignKey(Exam,on_delete=models.PROTECT,related_name="attempts")
    candidate=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="attempts")
    attempt_number=models.PositiveIntegerField()
    started_at=models.DateTimeField(default=timezone.now); expires_at=models.DateTimeField(); submitted_at=models.DateTimeField(null=True,blank=True)
    status=models.CharField(max_length=12,choices=[(IN_PROGRESS,"In progress"),(SUBMITTED,"Submitted"),(EXPIRED,"Expired")],default=IN_PROGRESS)
    score=models.DecimalField(max_digits=8,decimal_places=2,null=True,blank=True); max_score=models.DecimalField(max_digits=8,decimal_places=2,null=True,blank=True)
    percentage=models.DecimalField(max_digits=5,decimal_places=2,null=True,blank=True); passed=models.BooleanField(null=True,blank=True)
    verification_code=models.CharField(max_length=64,blank=True)
    rejoin_token=models.CharField(max_length=32,default=make_rejoin_token,unique=True,editable=False)
    class Meta: constraints=[models.UniqueConstraint(fields=["exam","candidate","attempt_number"],name="unique_attempt_number")]
    @property
    def is_open(self): return self.status==self.IN_PROGRESS and timezone.now()<self.expires_at
    def __str__(self): return f"{self.exam.code} / {self.candidate} / {self.attempt_number}"

class AttemptQuestion(models.Model):
    attempt=models.ForeignKey(Attempt,on_delete=models.CASCADE,related_name="attempt_questions")
    source_question=models.ForeignKey(Question,on_delete=models.PROTECT,related_name="attempt_snapshots")
    position=models.PositiveIntegerField(); question_code=models.CharField(max_length=60); question_type=models.CharField(max_length=10)
    stem=models.TextField(); explanation=models.TextField(blank=True); category_code=models.CharField(max_length=50); marks=models.DecimalField(max_digits=6,decimal_places=2)
    image_name=models.CharField(max_length=500,blank=True); image_alt_text=models.CharField(max_length=300,blank=True); image_sha256=models.CharField(max_length=64,blank=True)
    flagged=models.BooleanField(default=False); first_viewed_at=models.DateTimeField(null=True,blank=True); last_saved_at=models.DateTimeField(null=True,blank=True)
    class Meta: ordering=["position"]; constraints=[models.UniqueConstraint(fields=["attempt","position"],name="unique_attempt_position")]

class AttemptOption(models.Model):
    attempt_question=models.ForeignKey(AttemptQuestion,on_delete=models.CASCADE,related_name="snapshot_options")
    display_key=models.CharField(max_length=2); text=models.TextField(); is_correct=models.BooleanField()
    class Meta: ordering=["display_key"]; constraints=[models.UniqueConstraint(fields=["attempt_question","display_key"],name="unique_snapshot_key")]

class Response(models.Model):
    attempt_question=models.OneToOneField(AttemptQuestion,on_delete=models.CASCADE,related_name="response")
    selected_keys=models.JSONField(default=list); is_correct=models.BooleanField(null=True,blank=True); awarded_marks=models.DecimalField(max_digits=6,decimal_places=2,null=True,blank=True)
    saved_at=models.DateTimeField(auto_now=True)

class AuditEvent(models.Model):
    at=models.DateTimeField(default=timezone.now,editable=False); actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True)
    action=models.CharField(max_length=80); object_type=models.CharField(max_length=80); object_id=models.CharField(max_length=80)
    details=models.JSONField(default=dict,blank=True); ip_address=models.GenericIPAddressField(null=True,blank=True)
    previous_hash=models.CharField(max_length=64,blank=True); event_hash=models.CharField(max_length=64,unique=True)
    class Meta: ordering=["at","id"]
