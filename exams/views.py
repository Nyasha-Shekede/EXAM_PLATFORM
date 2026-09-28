import csv, io
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.http import Http404, HttpResponse, JsonResponse, FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.core.files.storage import default_storage
from django.utils import timezone
from django.views.decorators.http import require_POST
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.comments import Comment
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from .forms import CreateExamForm, ImportForm
from .importers import import_simple_questions
from .models import Assignment, Attempt, AttemptQuestion, Exam, Question, Response
from .services import client_ip,save_response,start_attempt,submit_attempt,audit

def home(request): return redirect("dashboard" if request.user.is_authenticated else "login")
@login_required
def dashboard(request):
    assignments=Assignment.objects.filter(candidate=request.user,active=True).select_related("exam","exam__module")
    rows=[]
    for a in assignments:
        attempts=list(Attempt.objects.filter(candidate=request.user,exam=a.exam).order_by("attempt_number"))
        open_attempt=next((x for x in attempts if x.status==Attempt.IN_PROGRESS and x.is_open),None)
        is_avail=a.exam.is_available()
        # Complete stealth: If exam is not currently open/available and student has no active in-progress attempt, conceal it completely!
        if not is_avail and not open_attempt:
            continue
        remaining=max(a.exam.max_attempts-len(attempts),0)
        # If all attempts are finished and no open attempt, hide card (results shown in completed attempts table below)
        if remaining==0 and not open_attempt:
            continue
        rows.append({"assignment":a,"exam":a.exam,"attempts":attempts,"open":open_attempt,"remaining":remaining,"available":is_avail})
    recent=Attempt.objects.filter(candidate=request.user).exclude(status=Attempt.IN_PROGRESS).select_related("exam").order_by("-submitted_at")[:10]
    staff_summary=None
    if request.user.is_staff:
        from django.contrib.auth import get_user_model
        User=get_user_model()
        completed_qs = Attempt.objects.exclude(status=Attempt.IN_PROGRESS)
        completed_count = completed_qs.count()
        passed_count = completed_qs.filter(passed=True).count()
        pass_rate = round((passed_count / completed_count) * 100) if completed_count > 0 else 0
        staff_summary={
            "exams_count": Exam.objects.count(),
            "candidates_count": User.objects.filter(is_staff=False).count(),
            "completed_attempts": completed_count,
            "pass_rate": pass_rate,
            "all_recent": completed_qs.select_related("exam","candidate").order_by("-submitted_at")[:8],
            "all_exams": Exam.objects.select_related("module").order_by("-created_at")[:12],
        }
    return render(request,"exams/dashboard.html",{"rows":rows,"recent":recent,"staff_summary":staff_summary})
@login_required
def begin(request,exam_id):
    if request.method != "POST":
        return redirect("dashboard")
    a=get_object_or_404(Assignment.objects.select_related("exam"),candidate=request.user,exam_id=exam_id,active=True)
    try: attempt=start_attempt(a.exam,request.user,client_ip(request))
    except ValidationError as e: messages.error(request,"; ".join(e.messages)); return redirect("dashboard")
    return redirect("question",attempt_id=attempt.id,position=1)

def owned_attempt(user, pk, allow_staff=True):
    qs = Attempt.objects.select_related("exam", "candidate")
    if allow_staff and user.is_staff:
        return get_object_or_404(qs, pk=pk)
    return get_object_or_404(qs, pk=pk, candidate=user)
@login_required
def question(request,attempt_id,position):
    attempt=owned_attempt(request.user,attempt_id)
    if attempt.status!=Attempt.IN_PROGRESS: return redirect("result",attempt_id=attempt.id)
    if timezone.now()>=attempt.expires_at:
        submit_attempt(attempt,expired=True,actor=request.user,ip=client_ip(request)); return redirect("result",attempt_id=attempt.id)
    aq=get_object_or_404(AttemptQuestion.objects.prefetch_related("snapshot_options"),attempt=attempt,position=position)
    if not aq.first_viewed_at: aq.first_viewed_at=timezone.now(); aq.save(update_fields=["first_viewed_at"])
    try: selected=aq.response.selected_keys
    except Response.DoesNotExist: selected=[]
    palette=attempt.attempt_questions.annotate(answered=Count("response",filter=~Q(response__selected_keys=[]))).values("position","flagged","answered").order_by("position")
    return render(request,"exams/question.html",{"attempt":attempt,"q":aq,"selected":selected,"palette":palette,"total":attempt.attempt_questions.count(),"now_epoch":int(timezone.now().timestamp()),"expires_epoch":int(attempt.expires_at.timestamp())})
@login_required
def answer(request,attempt_id,position):
    if request.method != "POST":
        return redirect("question", attempt_id=attempt_id, position=position)
    attempt=owned_attempt(request.user,attempt_id); aq=get_object_or_404(AttemptQuestion,attempt=attempt,position=position)
    selected=request.POST.getlist("selected")
    try: save_response(attempt,aq,selected,request.user,client_ip(request))
    except ValidationError as e:
        if request.headers.get("x-requested-with")=="XMLHttpRequest": return JsonResponse({"ok":False,"error":"; ".join(e.messages)},status=409)
        messages.error(request,"; ".join(e.messages)); return redirect("question",attempt.id,position)
    if request.headers.get("x-requested-with")=="XMLHttpRequest": return JsonResponse({"ok":True,"saved_at":timezone.now().isoformat()})
    target=request.POST.get("next","next")
    if target=="submit": return redirect("confirm_submit",attempt_id=attempt.id)
    newpos=max(1,min(attempt.attempt_questions.count(),position+( -1 if target=="previous" else 1)))
    return redirect("question",attempt.id,newpos)
@login_required
def flag_question(request,attempt_id,position):
    if request.method != "POST":
        return redirect("question", attempt_id=attempt_id, position=position)
    attempt=owned_attempt(request.user,attempt_id); aq=get_object_or_404(AttemptQuestion,attempt=attempt,position=position); aq.flagged=not aq.flagged; aq.save(update_fields=["flagged"]); return JsonResponse({"ok":True,"flagged":aq.flagged})
@login_required
def confirm_submit(request,attempt_id):
    attempt=owned_attempt(request.user,attempt_id); unanswered=attempt.attempt_questions.filter(Q(response__isnull=True)|Q(response__selected_keys=[])).count(); flagged=attempt.attempt_questions.filter(flagged=True).count()
    return render(request,"exams/confirm.html",{"attempt":attempt,"unanswered":unanswered,"flagged":flagged})
@login_required
def finish(request,attempt_id):
    if request.method != "POST":
        return redirect("confirm_submit", attempt_id=attempt_id)
    attempt=owned_attempt(request.user,attempt_id)
    submit_attempt(attempt,expired=timezone.now()>=attempt.expires_at,actor=request.user,ip=client_ip(request))
    return redirect("result",attempt_id=attempt.id)
@login_required
def result(request,attempt_id):
    attempt=owned_attempt(request.user,attempt_id,allow_staff=True)
    if attempt.status==Attempt.IN_PROGRESS: return redirect("question",attempt.id,1)
    category={}
    for aq in attempt.attempt_questions.select_related("response"):
        x=category.setdefault(aq.category_code,{"correct":0,"total":0}); x["total"]+=1; x["correct"]+=int(aq.response.is_correct)
    return render(request,"exams/result.html",{"attempt":attempt,"category":category.items()})
@login_required
def review(request,attempt_id):
    attempt=owned_attempt(request.user,attempt_id,allow_staff=True)
    if attempt.status==Attempt.IN_PROGRESS: raise Http404
    if not request.user.is_staff and not attempt.exam.show_answers_after: raise Http404
    return render(request,"exams/review.html",{"attempt":attempt,"questions":attempt.attempt_questions.prefetch_related("snapshot_options","response")})
@login_required
def result_pdf(request,attempt_id):
    attempt=owned_attempt(request.user,attempt_id,allow_staff=True)
    if attempt.status==Attempt.IN_PROGRESS: raise Http404
    response=HttpResponse(content_type="application/pdf"); response["Content-Disposition"]=f'attachment; filename="{attempt.exam.code}-attempt-{attempt.attempt_number}.pdf"'
    styles=getSampleStyleSheet(); title=ParagraphStyle("Title2",parent=styles["Title"],fontName="Helvetica-Bold",fontSize=20,textColor=colors.HexColor("#1483C6"),alignment=TA_CENTER)
    doc=SimpleDocTemplate(response,pagesize=A4,rightMargin=20*mm,leftMargin=20*mm,topMargin=18*mm,bottomMargin=18*mm,title="Examination Result Slip")
    story=[Paragraph("Examination Result Slip",title),Spacer(1,8*mm),Paragraph(settings.SITE_NAME,styles["Heading2"])]
    data=[["Candidate",attempt.candidate.get_full_name() or attempt.candidate.username],["Candidate ID",attempt.candidate.username],["Examination",attempt.exam.title],["Module",attempt.exam.module.title],["Attempt",str(attempt.attempt_number)],["Started",attempt.started_at.strftime("%Y-%m-%d %H:%M %Z")],["Submitted",attempt.submitted_at.strftime("%Y-%m-%d %H:%M %Z")],["Score",f"{attempt.score} / {attempt.max_score}"],["Percentage",f"{attempt.percentage}%"],["Pass mark",f"{attempt.exam.pass_mark}%"],["Result","PASS" if attempt.passed else "FAIL"]]
    t=Table(data,colWidths=[45*mm,105*mm]); t.setStyle(TableStyle([("BACKGROUND",(0,0),(0,-1),colors.HexColor("#E8F4FC")),("GRID",(0,0),(-1,-1),0.5,colors.HexColor("#CBD5E1")),("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),("VALIGN",(0,0),(-1,-1),"TOP"),("PADDING",(0,0),(-1,-1),7)])); story += [t,Spacer(1,10*mm),Paragraph("Verification hash",styles["Heading3"]),Paragraph(attempt.verification_code,ParagraphStyle("hash",parent=styles["BodyText"],fontName="Courier",fontSize=7,wordWrap="CJK")),Spacer(1,4*mm),Paragraph("This slip records the result held by the examination system. Verify against the portal record; the hash alone is not a digital signature.",styles["BodyText"])]
    doc.build(story); audit("RESULT_PDF_DOWNLOADED",attempt,request.user,{},client_ip(request)); return response

def staff_required(u): return u.is_active and u.is_staff

@login_required
def attempt_image(request,attempt_id,position):
    attempt=owned_attempt(request.user,attempt_id,allow_staff=True)
    aq=get_object_or_404(AttemptQuestion,attempt=attempt,position=position)
    if not aq.image_name or not default_storage.exists(aq.image_name): raise Http404
    content_type={".png":"image/png",".jpg":"image/jpeg",".jpeg":"image/jpeg",".webp":"image/webp"}.get(__import__("pathlib").Path(aq.image_name).suffix.lower(),"application/octet-stream")
    response=FileResponse(default_storage.open(aq.image_name,"rb"),content_type=content_type)
    response["Content-Disposition"]="inline"; response["X-Content-Type-Options"]="nosniff"; response["Cache-Control"]="private, max-age=300"
    return response

@user_passes_test(staff_required)
def protected_media(request,path):
    from pathlib import PurePosixPath
    p=PurePosixPath(path)
    if p.is_absolute() or ".." in p.parts or not default_storage.exists(path): raise Http404
    content_type={".png":"image/png",".jpg":"image/jpeg",".jpeg":"image/jpeg",".webp":"image/webp"}.get(p.suffix.lower(),"application/octet-stream")
    return FileResponse(default_storage.open(path,"rb"),content_type=content_type)

@user_passes_test(staff_required)
def import_view(request):
    result = None
    if request.method == "POST":
        form = ImportForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                result = import_simple_questions(
                    form.cleaned_data["spreadsheet"], form.cleaned_data["images"], request.user
                )
                if result["ok"]:
                    audit("QUESTIONS_IMPORTED", request.user, request.user,
                          {"count": result["imported"]}, client_ip(request))
            except Exception as exc:
                result = {"ok": False, "rows": 0, "imported": 0,
                          "errors": [{"row": "File", "question_code": "", "errors": [str(exc)]}]}
    else:
        form = ImportForm()
    return render(request, "exams/import.html", {"form": form, "result": result})

@user_passes_test(staff_required)
def template_download(request):
    headings = ["Category", "Question", "Option A", "Option B", "Option C",
                "Option D", "Correct Answer", "Image", "Image Description"]
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Questions"
    sheet.append(headings)
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = "A1:I1"
    widths = [24, 60, 32, 32, 32, 32, 20, 26, 48]
    notes = {
        "Category": "Optional. Topic/Chapter within this exam subject (e.g. Airspace, Weather Limits, Altimetry). Leave blank for General.",
        "Question": "Required. Enter the question stem.",
        "Option A": "Required.", "Option B": "Required.",
        "Option C": "Optional.", "Option D": "Optional.",
        "Correct Answer": "Use A for one correct answer or A,C for multiple correct answers.",
        "Image": "Optional. Format-agnostic: enter 'clouds' or 'clouds.png'. Select the picture file on upload.",
        "Image Description": "Required only when an image is referenced.",
    }
    for index, (heading, width) in enumerate(zip(headings, widths), 1):
        cell = sheet.cell(1, index)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1483C6")
        cell.alignment = Alignment(vertical="center")
        cell.comment = Comment(notes[heading], "Africa Drone Kings")
        sheet.column_dimensions[cell.column_letter].width = width
    sheet.row_dimensions[1].height = 28
    # Blank formatted rows make it obvious where to type without importing examples by accident.
    for row in range(2, 102):
        for column in range(1, 10):
            sheet.cell(row, column).alignment = Alignment(vertical="top", wrap_text=True)
    guide = workbook.create_sheet("Quick Guide")
    guide.column_dimensions["A"].width = 26
    guide.column_dimensions["B"].width = 90
    guide.append(["Step", "What to do"])
    guide.append(["1", "Fill one question per row on the Questions sheet for your chosen exam subject."])
    guide.append(["2", "For one correct answer type A, B, C, or D. For multiple correct answers type A,C (comma-separated)."])
    guide.append(["3", "Pictures are format-agnostic! Put the name (e.g. clouds or clouds.png) in Image and select the image files on upload."])
    guide.append(["4", "Upload when creating an exam to automatically import, publish, and assign to students."])
    for cell in guide[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1483C6")
    stream = io.BytesIO()
    workbook.save(stream)
    response = HttpResponse(stream.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="AFRICA_DRONE_KINGS_QUESTION_TEMPLATE.xlsx"'
    return response


@user_passes_test(staff_required)
def create_exam_view(request):
    import uuid, re
    from .models import Module, Category
    existing_modules = Module.objects.order_by("title")
    if request.method == "POST":
        form = CreateExamForm(request.POST, request.FILES)
        if form.is_valid():
            title = form.cleaned_data["title"]
            module_name = form.cleaned_data["module_name"].strip()
            duration = form.cleaned_data["duration_minutes"]
            pass_mark = form.cleaned_data["pass_mark"]
            max_attempts = form.cleaned_data["max_attempts"]
            show_answers = form.cleaned_data["show_answers_after"]
            spreadsheet = form.cleaned_data["spreadsheet"]
            images = form.cleaned_data["images"]
            candidates = form.cleaned_data["candidates"]

            # Import questions under the chosen subject module
            res = import_simple_questions(spreadsheet, images, request.user, default_module=module_name)
            if not res["ok"]:
                return render(request, "exams/create_exam.html", {
                    "form": form,
                    "import_errors": res["errors"],
                    "existing_modules": existing_modules,
                })

            imported_count = res["imported"]
            module_code = re.sub(r'[^A-Z0-9]+', '_', module_name.upper()).strip('_')[:50] or "MODULE"
            module, _ = Module.objects.get_or_create(code=module_code, defaults={"title": module_name})

            # Ensure all questions under this module are PUBLISHED so the exam can be taken immediately
            Question.objects.filter(module=module, status=Question.DRAFT).update(status=Question.PUBLISHED)
            published_pool = Question.objects.filter(module=module, status=Question.PUBLISHED).count()

            exam_code = re.sub(r'[^A-Za-z0-9_-]', '', title.upper().replace(' ', '-'))[:40] or f"EXAM-{uuid.uuid4().hex[:8].upper()}"
            if Exam.objects.filter(code=exam_code).exists():
                exam_code = f"{exam_code[:30]}-{uuid.uuid4().hex[:6].upper()}"

            q_count_input = form.cleaned_data.get("question_count")
            shuffle_questions = form.cleaned_data.get("shuffle_questions", True)
            shuffle_options = form.cleaned_data.get("shuffle_options", True)

            # Determine final question count: instructor specified or all available in pool
            if q_count_input and q_count_input > 0:
                final_question_count = min(q_count_input, published_pool)
            else:
                final_question_count = min(imported_count, published_pool)

            available_from = form.cleaned_data.get("available_from")
            available_until = form.cleaned_data.get("available_until")

            exam = Exam.objects.create(
                code=exam_code,
                title=title,
                module=module,
                duration_minutes=duration,
                pass_mark=pass_mark,
                max_attempts=max_attempts,
                question_count=final_question_count,
                shuffle_questions=shuffle_questions,
                shuffle_options=shuffle_options,
                show_answers_after=show_answers,
                available_from=available_from,
                available_until=available_until,
                status=Exam.PUBLISHED,
            )

            # Assign selected candidates
            for candidate in candidates:
                Assignment.objects.get_or_create(exam=exam, candidate=candidate)

            messages.success(request, f"Examination '{title}' created under module '{module.title}' with {imported_count} questions and assigned to {len(candidates)} student(s)!")
            return redirect("dashboard")
    else:
        form = CreateExamForm()

    return render(request, "exams/create_exam.html", {"form": form, "existing_modules": existing_modules})


@user_passes_test(staff_required)
@require_POST
def quick_add_candidate(request):
    import json, secrets
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid request payload."}, status=400)

    username = data.get("username", "").strip()
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()

    if not username:
        return JsonResponse({"ok": False, "error": "Candidate ID / Username is required."}, status=400)
    if User.objects.filter(username__iexact=username).exists():
        return JsonResponse({"ok": False, "error": f"Candidate with ID '{username}' already exists."}, status=400)

    name_parts = name.split(" ", 1)
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    default_pwd = f"ADK-{secrets.token_hex(3).upper()}!"
    user = User.objects.create_user(
        username=username,
        email=email,
        password=default_pwd,
        first_name=first_name,
        last_name=last_name,
        is_staff=False,
    )
    return JsonResponse({
        "ok": True,
        "id": user.pk,
        "label": f"{user.get_full_name() or user.username} ({user.username})",
        "username": user.username,
        "default_password": default_pwd,
    })

