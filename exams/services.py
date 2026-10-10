import hashlib, hmac, json, secrets
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction, connection
from django.db.models import Max
from django.utils import timezone
from .models import *

def client_ip(request):
    return request.META.get("HTTP_X_FORWARDED_FOR",request.META.get("REMOTE_ADDR","" )).split(",")[0].strip() or None

def client_user_agent(request):
    return (request.META.get("HTTP_USER_AGENT", "") or "")[:255] or None


@transaction.atomic
def audit(action,obj,actor=None,details=None,ip=None):
    # Serialize the global chain across Render/Gunicorn workers, including its first row.
    # Transaction-scoped PostgreSQL locks release on commit/rollback (no pool state leak).
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [1094994763])
    last=AuditEvent.objects.order_by("-id").first(); prev=last.event_hash if last else ""
    at=timezone.now()
    payload={"previous_hash":prev,"at":at.isoformat(),"actor":getattr(actor,"pk",None),"action":action,"object_type":obj.__class__.__name__,"object_id":str(obj.pk),"details":details or {}}
    event_hash=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
    return AuditEvent.objects.create(at=at,actor=actor,action=action,object_type=payload["object_type"],object_id=payload["object_id"],details=details or {},ip_address=ip,previous_hash=prev,event_hash=event_hash)

def validate_question(question):
    opts=list(question.options.all()); correct=[o for o in opts if o.is_correct]
    errors=[]
    if len(opts)<2: errors.append("At least two options are required.")
    if question.question_type==Question.SINGLE and len(correct)!=1: errors.append("Single-choice questions require exactly one correct option.")
    if question.question_type==Question.MULTIPLE and len(correct)<2: errors.append("Multiple-choice questions require at least two correct options.")
    return errors

def sample_stratified_questions(questions, count, rng):
    """Balance category counts where capacity allows; never exceed the target.

    Tie-breaking is randomized. When count is smaller than the number of
    categories, some categories necessarily remain untested. This is a sampling
    policy, not a claim of compliance with a particular aviation standard.
    """
    if count < 0 or count > len(questions):
        raise ValueError("Question target must fit the available pool")
    from collections import defaultdict
    by_category = defaultdict(list)
    for q in questions:
        by_category[q.category_id].append(q)
    for group in by_category.values():
        rng.shuffle(group)
    targets = {key: 0 for key in by_category}
    chosen = []
    for _ in range(count):
        eligible = [key for key, group in by_category.items() if targets[key] < len(group)]
        minimum = min(targets[key] for key in eligible)
        key = rng.choice([key for key in eligible if targets[key] == minimum])
        chosen.append(by_category[key][targets[key]])
        targets[key] += 1
    rng.shuffle(chosen)
    return chosen

def start_attempt(exam, candidate, ip=None, user_agent=None):
    # Expiry must survive a "no attempts remain" error; catch validation before
    # leaving the transaction, then raise only after committing the expiry record.
    error = None
    with transaction.atomic():
        try:
            result = _start_attempt(exam, candidate, ip=ip, user_agent=user_agent)
        except ValidationError as exc:
            error = exc
    if error is not None:
        raise error
    return result


def _start_attempt(exam, candidate, ip=None, user_agent=None):
    exam.refresh_from_db()
    assignment = Assignment.objects.select_for_update().filter(exam=exam, candidate=candidate, active=True).first()
    if not assignment:
        raise ValidationError("This exam is not assigned to this candidate.")
    if not exam.is_available():
        raise ValidationError("This exam is not currently available.")
    current = Attempt.objects.select_for_update().filter(exam=exam, candidate=candidate, status=Attempt.IN_PROGRESS).first()
    if current:
        if current.attempt_questions.count() == 0:
            raise ValidationError("This attempt has no question snapshot. Contact your instructor; records have been preserved.")
        if current.is_open:
            return current
        else:
            submit_attempt(current, expired=True, actor=candidate, ip=ip, user_agent=user_agent)
    count = Attempt.objects.filter(exam=exam, candidate=candidate).count()
    if count >= exam.max_attempts:
        raise ValidationError("No attempts remain.")
    pool = list(Question.objects.filter(module=exam.module, status=Question.PUBLISHED).select_related("category").prefetch_related("options"))
    valid = [q for q in pool if not validate_question(q)]
    if not valid:
        raise ValidationError(f"No published questions are available yet in '{exam.module.title}'. Contact your instructor.")
    q_target = exam.question_count
    if q_target < 1 or len(valid) < q_target:
        raise ValidationError(f"This exam requires {q_target} valid published questions; only {len(valid)} are ready. Contact your instructor.")
    rng = secrets.SystemRandom()
    chosen = sample_stratified_questions(valid, q_target, rng)
    if not exam.shuffle_questions:
        chosen = sorted(chosen, key=lambda q: (q.category.code if q.category else "", q.code))
    now = timezone.now()
    duration = exam.duration_minutes + assignment.extra_time_minutes
    attempt = Attempt.objects.create(exam=exam, candidate=candidate, attempt_number=count+1, started_at=now, expires_at=now+timedelta(minutes=duration))
    for pos, q in enumerate(chosen, 1):
        aq = AttemptQuestion.objects.create(attempt=attempt, source_question=q, position=pos, question_code=q.code, question_type=q.question_type, stem=q.stem, explanation=q.explanation, category_code=q.category.code, marks=q.marks, image_name=q.image.name if q.image else "", image_alt_text=q.image_alt_text, image_sha256=q.image_sha256)
        opts = list(q.options.all())
        if exam.shuffle_options:
            rng.shuffle(opts)
        for idx, o in enumerate(opts):
            AttemptOption.objects.create(attempt_question=aq, display_key=chr(65+idx), text=o.text, is_correct=o.is_correct)
    audit("ATTEMPT_STARTED", attempt, candidate, {
        "expires_at": attempt.expires_at.isoformat(),
        "question_count": len(chosen),
        "user_agent": user_agent,
    }, ip)
    from .emailing import attempt_notice
    attempt_notice(attempt, "started")
    return attempt

def save_response(attempt,aq,selected_keys,actor=None,ip=None,user_agent=None):
    if aq.attempt_id != attempt.pk:
        raise ValidationError("Question does not belong to this attempt.")
    if actor and actor != attempt.candidate:
        raise ValidationError("Security violation: Only the assigned candidate can submit responses for this attempt.")
    with transaction.atomic():
        locked=Attempt.objects.select_for_update().get(pk=attempt.pk)
        closed=locked.status!=Attempt.IN_PROGRESS or timezone.now()>=locked.expires_at
        if closed and locked.status==Attempt.IN_PROGRESS:
            submit_attempt(locked,expired=True,actor=actor,ip=ip,user_agent=user_agent)
        if closed:
            response = None
        else:
            valid=set(aq.snapshot_options.values_list("display_key",flat=True)); selected=sorted(set(selected_keys))
            if not set(selected)<=valid: raise ValidationError("Invalid option selection.")
            if aq.question_type==Question.SINGLE and len(selected)>1: raise ValidationError("Select one option only.")
            response,_=Response.objects.update_or_create(attempt_question=aq,defaults={"selected_keys":selected,"is_correct":None,"awarded_marks":None})
            aq.last_saved_at=timezone.now(); aq.save(update_fields=["last_saved_at"])

            # Detect and audit mid-exam IP shifts
            if ip:
                started_ev = AuditEvent.objects.filter(action="ATTEMPT_STARTED", object_id=str(attempt.pk)).first()
                if started_ev and started_ev.ip_address and started_ev.ip_address != ip:
                    if not AuditEvent.objects.filter(action="SUSPICIOUS_IP_CHANGE", object_id=str(attempt.pk), ip_address=ip).exists():
                        audit("SUSPICIOUS_IP_CHANGE", attempt, actor, {
                            "original_ip": started_ev.ip_address,
                            "new_ip": ip,
                            "user_agent": user_agent,
                            "question_position": aq.position,
                        }, ip=ip)

    if closed:
        raise ValidationError("The attempt is closed.")
    return response

@transaction.atomic
def submit_attempt(attempt,expired=False,actor=None,ip=None,user_agent=None):
    attempt=Attempt.objects.select_for_update().get(pk=attempt.pk)
    if attempt.status!=Attempt.IN_PROGRESS: return attempt
    if actor and actor != attempt.candidate:
        raise ValidationError("Security violation: Only the assigned candidate can finish this attempt.")
    # The deadline is authoritative even when callers forget to request expiry.
    expired = expired or timezone.now() >= attempt.expires_at
    total=Decimal("0"); maximum=Decimal("0")
    for aq in attempt.attempt_questions.prefetch_related("snapshot_options").all():
        maximum += aq.marks
        correct={o.display_key for o in aq.snapshot_options.all() if o.is_correct}
        try: response=aq.response
        except Response.DoesNotExist: response=Response.objects.create(attempt_question=aq,selected_keys=[])
        selected=set(response.selected_keys)
        ok=selected==correct
        awarded=aq.marks if ok else Decimal("0")
        response.is_correct=ok; response.awarded_marks=awarded; response.save(update_fields=["is_correct","awarded_marks","saved_at"])
        total += awarded
    pct=(total/maximum*100 if maximum else Decimal("0")).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP)
    submitted=timezone.now(); passed=pct>=attempt.exam.pass_mark
    canonical=f"{attempt.id}|{attempt.candidate_id}|{attempt.exam_id}|{total}|{maximum}|{pct}|{submitted.isoformat()}"
    code=hmac.new(settings.SECRET_KEY.encode(),canonical.encode(),hashlib.sha256).hexdigest()
    attempt.score=total; attempt.max_score=maximum; attempt.percentage=pct; attempt.passed=passed; attempt.submitted_at=submitted; attempt.status=Attempt.EXPIRED if expired else Attempt.SUBMITTED; attempt.verification_code=code
    attempt.save(update_fields=["score","max_score","percentage","passed","submitted_at","status","verification_code"])
    audit("ATTEMPT_EXPIRED" if expired else "ATTEMPT_SUBMITTED",attempt,actor,{
        "score":str(total),
        "max_score":str(maximum),
        "percentage":str(pct),
        "passed":passed,
        "user_agent":user_agent,
    },ip)
    from .emailing import attempt_notice
    attempt_notice(attempt, "submitted")
    return attempt


def verify_audit_chain():
    prev=""
    for e in AuditEvent.objects.order_by("id"):
        payload={"previous_hash":e.previous_hash,"at":e.at.isoformat(),"actor":e.actor_id,"action":e.action,"object_type":e.object_type,"object_id":e.object_id,"details":e.details or {}}
        expected=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
        if e.previous_hash!=prev or not hmac.compare_digest(e.event_hash,expected): return False,e.id
        prev=e.event_hash
    return True,None
