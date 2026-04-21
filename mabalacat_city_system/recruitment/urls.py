"""URL routing for recruitment API endpoints."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ApplicantViewSet,
    ApplicationDocumentViewSet,
    ApplicationViewSet,
    AppointmentViewSet,
    ExamResultViewSet,
    ExamScheduleViewSet,
    InterviewResultViewSet,
    InterviewScheduleViewSet,
    JobPostingViewSet,
    RankingEntryViewSet,
    RankingListViewSet,
)

router = DefaultRouter()
router.register(r"job-postings", JobPostingViewSet, basename="job-posting")
router.register(r"applicants", ApplicantViewSet, basename="applicant")
router.register(r"applications", ApplicationViewSet, basename="application")
router.register(r"application-documents", ApplicationDocumentViewSet, basename="application-document")
router.register(r"exam-schedules", ExamScheduleViewSet, basename="exam-schedule")
router.register(r"exam-results", ExamResultViewSet, basename="exam-result")
router.register(r"interview-schedules", InterviewScheduleViewSet, basename="interview-schedule")
router.register(r"interview-results", InterviewResultViewSet, basename="interview-result")
router.register(r"ranking-lists", RankingListViewSet, basename="ranking-list")
router.register(r"ranking-entries", RankingEntryViewSet, basename="ranking-entry")
router.register(r"appointments", AppointmentViewSet, basename="appointment")

urlpatterns = [
    path("", include(router.urls)),
]
