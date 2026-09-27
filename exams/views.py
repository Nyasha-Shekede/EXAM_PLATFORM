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
from .forms import ImportForm
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
        rows.append({"assignment":a,"exam":a.exam,"attempts":attempts,"open":open_attempt,"remaining":max(a.exam.max_attempts-len(attempts),0),"available":a.exam.is_available()})
    recent=Attempt.objects.filter(candidate=request.user).exclude(status=Attempt.IN_PROGRESS).select_related("exam").order_by("-submitted_at")[:10]
    staff_summary=None
    if request.user.is_staff:
        from django.contrib.auth import get_user_model
        User=get_user_model()
        staff_summary={
            "exams_count":Exam.objects.count(),
            "questions_count":Question.objects.count(),
            "candidates_count":User.objects.filter(is_staff=False).count(),
            "completed_attempts":Attempt.objects.exclude(status=Attempt.IN_PROGRESS).count(),
            "all_recent":Attempt.objects.exclude(status=Attempt.IN_PROGRESS).select_related("exam","candidate").order_by("-submitted_at")[:8],
        }
    return render(request,"exams/dashboard.html",{"rows":rows,"recent":recent,"staff_summary":staff_summary})
@login_required
@require_POST
def begin(request,exam_id):
    a=get_object_or_404(Assignment.objects.select_related("exam"),candidate=request.user,exam_id=exam_id,active=True)
    try: attempt=start_attempt(a.exam,request.user,client_ip(request))
    except ValidationError as e: messages.error(request,"; ".join(e.messages)); return redirect("dashboard")
    return redirect("question",attempt_id=attempt.id,position=1)

def owned_attempt(user,pk): return get_object_or_404(Attempt.objects.select_related("exam","candidate"),pk=pk,candidate=user)
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
    palette=attempt.attempt_questions.annotate(answered=Count("response",filter=~Q(response__selected_keys=[]))).values("position","flagged","answered")
    return render(request,"exams/question.html",{"attempt":attempt,"q":aq,"selected":selected,"palette":palette,"total":attempt.attempt_questions.count(),"now_epoch":int(timezone.now().timestamp()),"expires_epoch":int(attempt.expires_at.timestamp())})
@login_required
@require_POST
def answer(request,attempt_id,position):
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
@require_POST
def flag_question(request,attempt_id,position):
    attempt=owned_attempt(request.user,attempt_id); aq=get_object_or_404(AttemptQuestion,attempt=attempt,position=position); aq.flagged=not aq.flagged; aq.save(update_fields=["flagged"]); return JsonResponse({"ok":True,"flagged":aq.flagged})
@login_required
def confirm_submit(request,attempt_id):
    attempt=owned_attempt(request.user,attempt_id); unanswered=attempt.attempt_questions.filter(Q(response__isnull=True)|Q(response__selected_keys=[])).count(); flagged=attempt.attempt_questions.filter(flagged=True).count()
    return render(request,"exams/confirm.html",{"attempt":attempt,"unanswered":unanswered,"flagged":flagged})
@login_required
@require_POST
def finish(request,attempt_id):
    attempt=owned_attempt(request.user,attempt_id)
    submit_attempt(attempt,expired=timezone.now()>=attempt.expires_at,actor=request.user,ip=client_ip(request))
    return redirect("result",attempt_id=attempt.id)
@login_required
def result(request,attempt_id):
    attempt=owned_attempt(request.user,attempt_id)
    if attempt.status==Attempt.IN_PROGRESS: return redirect("question",attempt.id,1)
    category={}
    for aq in attempt.attempt_questions.select_related("response"):
        x=category.setdefault(aq.category_code,{"correct":0,"total":0}); x["total"]+=1; x["correct"]+=int(aq.response.is_correct)
    return render(request,"exams/result.html",{"attempt":attempt,"category":category.items()})
@login_required
def review(request,attempt_id):
    attempt=owned_attempt(request.user,attempt_id)
    if attempt.status==Attempt.IN_PROGRESS or not attempt.exam.show_answers_after: raise Http404
    return render(request,"exams/review.html",{"attempt":attempt,"questions":attempt.attempt_questions.prefetch_related("snapshot_options","response")})
@login_required
def result_pdf(request,attempt_id):
    attempt=owned_attempt(request.user,attempt_id)
    if attempt.status==Attempt.IN_PROGRESS: raise Http404
    response=HttpResponse(content_type="application/pdf"); response["Content-Disposition"]=f'attachment; filename="{attempt.exam.code}-attempt-{attempt.attempt_number}.pdf"'
    styles=getSampleStyleSheet(); title=ParagraphStyle("Title2",parent=styles["Title"],fontName="Helvetica-Bold",fontSize=20,textColor=colors.HexColor("#12372A"),alignment=TA_CENTER)
    doc=SimpleDocTemplate(response,pagesize=A4,rightMargin=20*mm,leftMargin=20*mm,topMargin=18*mm,bottomMargin=18*mm,title="Examination Result Slip")
    story=[Paragraph("Examination Result Slip",title),Spacer(1,8*mm),Paragraph(settings.SITE_NAME,styles["Heading2"])]
    data=[["Candidate",attempt.candidate.get_full_name() or attempt.candidate.username],["Candidate ID",attempt.candidate.username],["Examination",attempt.exam.title],["Module",attempt.exam.module.title],["Attempt",str(attempt.attempt_number)],["Started",attempt.started_at.strftime("%Y-%m-%d %H:%M %Z")],["Submitted",attempt.submitted_at.strftime("%Y-%m-%d %H:%M %Z")],["Score",f"{attempt.score} / {attempt.max_score}"],["Percentage",f"{attempt.percentage}%"],["Pass mark",f"{attempt.exam.pass_mark}%"],["Result","PASS" if attempt.passed else "FAIL"]]
    t=Table(data,colWidths=[45*mm,105*mm]); t.setStyle(TableStyle([("BACKGROUND",(0,0),(0,-1),colors.HexColor("#E7F0EC")),("GRID",(0,0),(-1,-1),0.5,colors.HexColor("#AAB8B1")),("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),("VALIGN",(0,0),(-1,-1),"TOP"),("PADDING",(0,0),(-1,-1),7)])); story += [t,Spacer(1,10*mm),Paragraph("Verification hash",styles["Heading3"]),Paragraph(attempt.verification_code,ParagraphStyle("hash",parent=styles["BodyText"],fontName="Courier",fontSize=7,wordWrap="CJK")),Spacer(1,4*mm),Paragraph("This slip records the result held by the examination system. Verify against the portal record; the hash alone is not a digital signature.",styles["BodyText"])]
    doc.build(story); audit("RESULT_PDF_DOWNLOADED",attempt,request.user,{},client_ip(request)); return response

def staff_required(u): return u.is_active and u.is_staff

@login_required
def attempt_image(request,attempt_id,position):
    attempt=owned_attempt(request.user,attempt_id)
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
    headings = ["Module", "Category", "Question", "Option A", "Option B", "Option C",
                "Option D", "Correct Answer", "Image", "Image Description"]
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Questions"
    sheet.append(headings)
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = "A1:J1"
    widths = [22, 22, 58, 32, 32, 32, 32, 20, 28, 48]
    notes = {
        "Module": "Required. Example: Air Law. The system creates the module if needed.",
        "Category": "Optional. Leave blank to use General.",
        "Question": "Required. Enter the full question.",
        "Option A": "Required.", "Option B": "Required.",
        "Option C": "Optional.", "Option D": "Optional.",
        "Correct Answer": "Use A for one correct answer or A,C for multiple correct answers.",
        "Image": "Optional. Enter the exact picture filename, e.g. chart.png, then select that picture on upload.",
        "Image Description": "Required only for a picture. Describe it without revealing the answer.",
    }
    for index, (heading, width) in enumerate(zip(headings, widths), 1):
        cell = sheet.cell(1, index)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="156B52")
        cell.alignment = Alignment(vertical="center")
        cell.comment = Comment(notes[heading], "Exam Platform")
        sheet.column_dimensions[cell.column_letter].width = width
    sheet.row_dimensions[1].height = 28
    # Blank formatted rows make it obvious where to type without importing examples by accident.
    for row in range(2, 102):
        for column in range(1, 11):
            sheet.cell(row, column).alignment = Alignment(vertical="top", wrap_text=True)
    guide = workbook.create_sheet("Quick Guide")
    guide.column_dimensions["A"].width = 26
    guide.column_dimensions["B"].width = 90
    guide.append(["Step", "What to do"])
    guide.append(["1", "Fill one question per row on the Questions sheet."])
    guide.append(["2", "For one correct answer type A, B, C, or D. For multiple correct answers type A,C (comma-separated)."])
    guide.append(["3", "Pictures are optional. Put the exact filename in Image and select the picture when uploading the sheet."])
    guide.append(["4", "Upload once. Valid rows are imported as drafts for instructor review."])
    for cell in guide[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="156B52")
    stream = io.BytesIO()
    workbook.save(stream)
    response = HttpResponse(stream.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="SIMPLE_QUESTION_TEMPLATE.xlsx"'
    return response
