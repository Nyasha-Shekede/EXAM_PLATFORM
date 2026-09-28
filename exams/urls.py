from django.urls import path
from . import views
urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("exams/new/", views.create_exam_view, name="create_exam"),
    path("candidates/quick-add/", views.quick_add_candidate, name="quick_add_candidate"),
    path("exams/<uuid:exam_id>/begin/", views.begin, name="begin"),
    path("attempts/<uuid:attempt_id>/questions/<int:position>/", views.question, name="question"),
    path("attempts/<uuid:attempt_id>/questions/<int:position>/answer/", views.answer, name="answer"),
    path("attempts/<uuid:attempt_id>/questions/<int:position>/flag/", views.flag_question, name="flag_question"),
    path("attempts/<uuid:attempt_id>/confirm/", views.confirm_submit, name="confirm_submit"),
    path("attempts/<uuid:attempt_id>/finish/", views.finish, name="finish"),
    path("attempts/<uuid:attempt_id>/result/", views.result, name="result"),
    path("attempts/<uuid:attempt_id>/review/", views.review, name="review"),
    path("attempts/<uuid:attempt_id>/result.pdf/", views.result_pdf, name="result_pdf"),
    path("attempts/<uuid:attempt_id>/questions/<int:position>/image/", views.attempt_image, name="attempt_image"),
    path("protected-media/<path:path>", views.protected_media, name="protected_media"),
    path("staff/import/", views.import_view, name="import_questions"),
    path("staff/import/template.xlsx", views.template_download, name="import_template"),
]
