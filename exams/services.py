import hashlib, hmac, json, secrets
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from .models import *

def client_ip(request):
    return request.META.get("HTTP_X_FORWARDED_FOR",request.META.get("REMOTE_ADDR","" )).split(",")[0].strip() or None

def client_user_agent(request):
    return (request.META.get("HTTP_USER_AGENT", "") or "")[:255] or None


def audit(action,obj,actor=None,details=None,ip=None):
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
    """
    Balanced Stratified Section Sampling (Civil Aviation Exam Standard).
    Samples questions fairly across all sections/categories in the pool,
    guaranteeing that every syllabus area is tested without bias or omission.
    """
    if len(questions) <= count:
        chosen = list(questions)
        rng.shuffle(chosen)
        return chosen

    from collections import defaultdict
    by_category = defaultdict(list)
    for q in questions:
        by_category[q.category_id].append(q)

    # Single category in pool: uniform random sampling
    if len(by_category) <= 1:
        return rng.sample(questions, count)

    for cat_id in by_category:
        rng.shuffle(by_category[cat_id])

    targets = {}
    available = {cat_id: len(qs) for cat_id, qs in by_category.items()}
    remaining_needed = count
    active_cats = set(by_category.keys())

    # Distribute quotas iteratively so smaller sections contribute all they have
    # and larger sections absorb the remaining deficit evenly
    while remaining_needed > 0 and active_cats:
        fair_share = max(1, remaining_needed // len(active_cats))
        capped = False
        for cat_id in list(active_cats):
            avail = available[cat_id] - targets.get(cat_id, 0)
            if avail <= fair_share:
                alloc = avail
                targets[cat_id] = targets.get(cat_id, 0) + alloc
                remaining_needed -= alloc
                active_cats.remove(cat_id)
                capped = True
        if not capped:
            for cat_id in list(active_cats):
                alloc = min(fair_share, remaining_needed)
                targets[cat_id] = targets.get(cat_id, 0) + alloc
                remaining_needed -= alloc
                if targets[cat_id] >= available[cat_id]:
                    active_cats.remove(cat_id)
                if remaining_needed == 0:
                    break

    if remaining_needed > 0:
        for cat_id, qs in by_category.items():
            can_take = len(qs) - targets.get(cat_id, 0)
            take = min(can_take, remaining_needed)
            targets[cat_id] = targets.get(cat_id, 0) + take
            remaining_needed -= take
            if remaining_needed == 0:
                break

    chosen = []
    for cat_id, target in targets.items():
        chosen.extend(by_category[cat_id][:target])

    rng.shuffle(chosen)
    return chosen

def reconcile_exam_pools():
    """
    Self-healing routine:
    1. Ensures draft questions are published.
    2. Heals modules with zero questions if questions exist under similar module titles (e.g. Meterology vs Meteorology).
    3. Heals exams with question_count=0 so candidates always receive their full question set.
    """
    from django.db.models import Q
    for exam in Exam.objects.select_related("module").all():
        Question.objects.filter(module=exam.module, status=Question.DRAFT).update(status=Question.PUBLISHED)
        pool_count = Question.objects.filter(module=exam.module, status=Question.PUBLISHED).count()
        if pool_count == 0:
            stem = exam.module.code[:4] if len(exam.module.code) >= 4 else exam.module.code
            similar = Module.objects.filter(
                Q(code__icontains=stem) | Q(title__icontains=stem)
            ).exclude(code=exam.module.code)
            for sm in similar:
                sm_qs = Question.objects.filter(module=sm)
                if sm_qs.exists():
                    sm_qs.update(module=exam.module, status=Question.PUBLISHED)
                    pool_count = Question.objects.filter(module=exam.module, status=Question.PUBLISHED).count()
                    break
        if pool_count > 0 and (exam.question_count == 0 or exam.question_count > pool_count):
            exam.question_count = pool_count
            exam.save(update_fields=["question_count"])

@transaction.atomic
def start_attempt(exam, candidate, ip=None, user_agent=None):
    reconcile_exam_pools()
    exam.refresh_from_db()
    assignment = Assignment.objects.select_for_update().filter(exam=exam, candidate=candidate, active=True).first()
    if not assignment:
        raise ValidationError("This exam is not assigned to this candidate.")
    if not exam.is_available():
        raise ValidationError("This exam is not currently available.")
    current = Attempt.objects.select_for_update().filter(exam=exam, candidate=candidate, status=Attempt.IN_PROGRESS).first()
    if current:
        # Discard broken attempt if created with 0 questions due to previous pool mismatch
        if current.attempt_questions.count() == 0:
            current.delete()
            current = None
        elif current.is_open:
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
    q_target = min(exam.question_count or len(valid), len(valid))
    q_target = max(1, q_target)
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
    if actor and actor != attempt.candidate:
        raise ValidationError("Security violation: Only the assigned candidate can submit responses for this attempt.")
    with transaction.atomic():
        locked=Attempt.objects.select_for_update().get(pk=attempt.pk)
        closed=locked.status!=Attempt.IN_PROGRESS or timezone.now()>=locked.expires_at
    if closed:
        if locked.status==Attempt.IN_PROGRESS: submit_attempt(locked,expired=True,actor=actor,ip=ip,user_agent=user_agent)
        raise ValidationError("The attempt is closed.")
    with transaction.atomic():
        locked=Attempt.objects.select_for_update().get(pk=attempt.pk)
        if locked.status!=Attempt.IN_PROGRESS or timezone.now()>=locked.expires_at:
            raise ValidationError("The attempt is closed.")
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

        return response

@transaction.atomic
def submit_attempt(attempt,expired=False,actor=None,ip=None,user_agent=None):
    attempt=Attempt.objects.select_for_update().get(pk=attempt.pk)
    if attempt.status!=Attempt.IN_PROGRESS: return attempt
    if not expired and actor and actor != attempt.candidate:
        raise ValidationError("Security violation: Only the assigned candidate can finish this attempt.")
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
