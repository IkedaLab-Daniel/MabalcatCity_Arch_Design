"""ViewSets for recruitment API endpoints."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Count, Prefetch
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import (
    Applicant,
    Application,
    ApplicationDocument,
    Appointment,
    ExamResult,
    ExamSchedule,
    InterviewResult,
    InterviewSchedule,
    JobPosting,
    RankingEntry,
    RankingList,
)
from .pagination import RecruitmentPagination
from .permissions import IsApplicant, IsHRHeadOrAdmin, IsHRStaff
from .serializers import (
    ApplicantSerializer,
    ApplicationDocumentSerializer,
    ApplicationSerializer,
    AppointmentSerializer,
    ExamResultSerializer,
    ExamScheduleSerializer,
    InterviewResultSerializer,
    InterviewScheduleSerializer,
    JobPostingSerializer,
    RankingEntrySerializer,
    RankingListSerializer,
)
from .utils import error_response


HR_STAFF_ROLES = {"HR_STAFF", "HR_HEAD", "ADMIN"}


def _is_hr_staff(user) -> bool:
    """Return True when user belongs to authorized HR roles."""

    return bool(user and user.is_authenticated and getattr(user, "role", None) in HR_STAFF_ROLES)


class BaseRecruitmentViewSet(viewsets.ModelViewSet):
    """Base viewset with shared JWT auth, filtering, pagination, and error shape."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    pagination_class = RecruitmentPagination

    def handle_exception(self, exc):
        """Normalize exception responses to a consistent API error payload."""

        response = super().handle_exception(exc)
        if response is None:
            return response

        if isinstance(response.data, dict) and {"detail", "code", "field_errors"}.issubset(response.data.keys()):
            return response

        if isinstance(response.data, dict) and "detail" in response.data and len(response.data) == 1:
            detail_obj = response.data["detail"]
            detail = str(detail_obj)
            code = str(getattr(detail_obj, "code", "error"))
            response.data = {"detail": detail, "code": code, "field_errors": {}}
            return response

        field_errors = response.data if isinstance(response.data, dict) else {}
        response.data = {
            "detail": "Validation error.",
            "code": "validation_error",
            "field_errors": field_errors,
        }
        return response


class JobPostingViewSet(BaseRecruitmentViewSet):
    """CRUD and workflow actions for recruitment job postings."""

    serializer_class = JobPostingSerializer
    filterset_fields = ["status", "department", "employment_type", "salary_grade"]
    search_fields = ["title", "position_code__id"]
    ordering_fields = ["date_posted", "deadline"]
    ordering = ["-date_posted"]

    def get_queryset(self):
        """Return optimized posting queryset with application count annotation."""

        return (
            JobPosting.objects.select_related("position_code", "department", "posted_by")
            .annotate(applications_count=Count("applications"))
            .all()
        )

    def get_permissions(self):
        """Allow public reads, but restrict writes to HR staff."""

        if self.action in {"list", "retrieve"}:
            return [AllowAny()]
        return [IsAuthenticated(), IsHRStaff()]

    def perform_create(self, serializer):
        """Set the posting user on creation."""

        serializer.save(posted_by=self.request.user)

    @action(detail=True, methods=["patch"], url_path="close-posting")
    def close_posting(self, request, pk=None):
        """Close a posting if deadline passed or when manually forced."""

        posting = self.get_object()
        if posting.status == JobPosting.Status.CLOSED:
            return error_response("Job posting is already closed.", "already_closed")

        manually_closed = bool(request.data.get("manually_closed", False))
        if posting.deadline > timezone.now() and not manually_closed:
            return error_response(
                "Deadline has not passed. Set manually_closed=true to force close.",
                "deadline_not_reached",
            )

        posting.status = JobPosting.Status.CLOSED
        posting.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(posting).data, status=status.HTTP_200_OK)


class ApplicantViewSet(BaseRecruitmentViewSet):
    """Manage applicant profiles for HR and applicant self-service."""

    serializer_class = ApplicantSerializer
    search_fields = ["last_name", "first_name", "email", "eligibility"]
    ordering_fields = ["last_name", "first_name", "created_at"]
    ordering = ["last_name", "first_name"]

    def get_queryset(self):
        """Scope applicants by role while keeping related data eager-loaded."""

        queryset = Applicant.objects.all()
        user = self.request.user

        if _is_hr_staff(user):
            return queryset

        if user.is_authenticated and getattr(user, "role", None) == "APPLICANT":
            return queryset.filter(email__iexact=user.email)

        return queryset.none()

    def get_permissions(self):
        """Allow HR full management while applicants can manage own profile."""

        user_role = getattr(self.request.user, "role", None)
        if _is_hr_staff(self.request.user):
            return [IsAuthenticated(), IsHRStaff()]

        if user_role == "APPLICANT":
            if self.action in {"list", "retrieve"}:
                return [IsAuthenticated(), IsApplicant()]
            if self.action in {"create", "update", "partial_update"}:
                return [IsAuthenticated()]

        return [IsAuthenticated(), IsHRStaff()]

    def perform_create(self, serializer):
        """Prevent applicants from creating profiles for other emails."""

        user = self.request.user
        if not _is_hr_staff(user) and getattr(user, "role", None) != "APPLICANT":
            raise PermissionDenied("Only applicant users or HR staff can create applicant records.")
        if not _is_hr_staff(user) and serializer.validated_data.get("email", "").lower() != user.email.lower():
            raise PermissionDenied("Applicants can only create a profile matching their account email.")
        serializer.save()


class ApplicationViewSet(BaseRecruitmentViewSet):
    """Manage application lifecycle and bulk status transitions."""

    serializer_class = ApplicationSerializer
    filterset_fields = {
        "application_status": ["exact"],
        "job_posting": ["exact"],
        "date_applied": ["date", "gte", "lte"],
    }
    search_fields = ["applicant__last_name", "applicant__first_name", "applicant__email"]
    ordering_fields = ["date_applied", "application_status", "created_at"]
    ordering = ["-date_applied"]

    def get_queryset(self):
        """Return role-scoped applications with related objects preloaded."""

        queryset = Application.objects.select_related(
            "applicant",
            "job_posting",
            "job_posting__department",
            "job_posting__position_code",
            "processed_by",
        )
        user = self.request.user

        if _is_hr_staff(user):
            return queryset

        if user.is_authenticated and getattr(user, "role", None) == "APPLICANT":
            return queryset.filter(applicant__email__iexact=user.email)

        return queryset.none()

    def get_permissions(self):
        """Allow applicant create/read-own, HR full access for all actions."""

        if _is_hr_staff(self.request.user):
            return [IsAuthenticated(), IsHRStaff()]

        if self.action in {"update", "partial_update", "destroy", "update_status", "shortlist"}:
            return [IsAuthenticated(), IsHRStaff()]

        user = self.request.user
        if getattr(user, "role", None) == "APPLICANT":
            if self.action in {"list", "retrieve"}:
                return [IsAuthenticated(), IsApplicant()]
            if self.action == "create":
                return [IsAuthenticated()]

        return [IsAuthenticated(), IsHRStaff()]

    def perform_create(self, serializer):
        """Enforce applicant ownership and auto-tag HR processor when applicable."""

        user = self.request.user
        applicant = serializer.validated_data["applicant"]

        if not _is_hr_staff(user) and getattr(user, "role", None) != "APPLICANT":
            raise PermissionDenied("Only applicant users or HR staff can create applications.")

        if not _is_hr_staff(user) and applicant.email.lower() != user.email.lower():
            raise PermissionDenied(
                "Applicants may only submit applications tied to their own email."
            )

        if _is_hr_staff(user):
            serializer.save(processed_by=user)
        else:
            serializer.save()

    @action(detail=True, methods=["patch"], url_path="update-status")
    def update_status(self, request, pk=None):
        """Update application status, restricted to HR roles with audit trail."""

        if not _is_hr_staff(request.user):
            return error_response(
                "Only HR staff can update application status.",
                "forbidden",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        instance = self.get_object()
        new_status = request.data.get("application_status")
        remarks = request.data.get("remarks")

        valid_statuses = {choice[0] for choice in Application.ApplicationStatus.choices}
        if new_status not in valid_statuses:
            return error_response(
                "Invalid application_status value.",
                "invalid_status",
                field_errors={"application_status": ["Not a valid status option."]},
            )

        instance.application_status = new_status
        if remarks is not None:
            instance.remarks = remarks
        instance.processed_by = request.user
        instance.save(update_fields=["application_status", "remarks", "processed_by", "updated_at"])
        return Response(self.get_serializer(instance).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="shortlist")
    def shortlist(self, request):
        """Bulk move selected applications to SHORTLISTED status."""

        if not _is_hr_staff(request.user):
            return error_response(
                "Only HR staff can shortlist applications.",
                "forbidden",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        application_ids = request.data.get("application_ids", [])
        if not isinstance(application_ids, list) or not application_ids:
            return error_response(
                "application_ids must be a non-empty list.",
                "invalid_payload",
                field_errors={"application_ids": ["Provide at least one application ID."]},
            )

        queryset = self.get_queryset().filter(pk__in=application_ids)
        existing_ids = set(queryset.values_list("id", flat=True))
        missing_ids = sorted(set(application_ids) - existing_ids)

        with transaction.atomic():
            queryset.update(
                application_status=Application.ApplicationStatus.SHORTLISTED,
                processed_by=request.user,
                updated_at=timezone.now(),
            )

        return Response(
            {
                "updated_count": queryset.count(),
                "missing_ids": missing_ids,
            },
            status=status.HTTP_200_OK,
        )


class ApplicationDocumentViewSet(BaseRecruitmentViewSet):
    """Manage documentary requirements and verification status."""

    serializer_class = ApplicationDocumentSerializer
    filterset_fields = ["document_type", "is_verified", "application"]
    ordering_fields = ["uploaded_at", "created_at"]
    ordering = ["-uploaded_at"]

    def get_queryset(self):
        """Return role-scoped documents with related app and user data."""

        queryset = ApplicationDocument.objects.select_related(
            "application",
            "application__applicant",
            "verified_by",
        )
        user = self.request.user
        if _is_hr_staff(user):
            return queryset
        if user.is_authenticated and getattr(user, "role", None) == "APPLICANT":
            return queryset.filter(application__applicant__email__iexact=user.email)
        return queryset.none()

    def get_permissions(self):
        """Applicants can upload/read own docs; HR can manage all docs."""

        if _is_hr_staff(self.request.user):
            return [IsAuthenticated(), IsHRStaff()]

        if getattr(self.request.user, "role", None) == "APPLICANT":
            if self.action in {"list", "retrieve"}:
                return [IsAuthenticated(), IsApplicant()]
            return [IsAuthenticated()]

        return [IsAuthenticated(), IsHRStaff()]

    def perform_create(self, serializer):
        """Ensure applicants only upload documents for their own applications."""

        user = self.request.user
        if not _is_hr_staff(user) and getattr(user, "role", None) != "APPLICANT":
            raise PermissionDenied("Only applicant users or HR staff can upload documents.")
        application = serializer.validated_data["application"]
        if not _is_hr_staff(user) and application.applicant.email.lower() != user.email.lower():
            raise PermissionDenied("Applicants can only upload documents for their own applications.")
        serializer.save()

    def perform_update(self, serializer):
        """Set verifier when verified by HR users."""

        is_verified = serializer.validated_data.get("is_verified", serializer.instance.is_verified)
        if is_verified and _is_hr_staff(self.request.user):
            serializer.save(verified_by=self.request.user)
            return
        serializer.save()


class ExamScheduleViewSet(BaseRecruitmentViewSet):
    """CRUD viewset for exam schedules."""

    serializer_class = ExamScheduleSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filterset_fields = ["job_posting", "exam_date"]
    ordering_fields = ["exam_date", "exam_time", "created_at"]
    ordering = ["exam_date", "exam_time"]

    def get_queryset(self):
        """Return exam schedules with posting and creator loaded."""

        return ExamSchedule.objects.select_related("job_posting", "created_by")

    def perform_create(self, serializer):
        """Set creator on schedule creation."""

        serializer.save(created_by=self.request.user)


class ExamResultViewSet(BaseRecruitmentViewSet):
    """CRUD viewset for exam result scoring."""

    serializer_class = ExamResultSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filterset_fields = ["application", "exam_schedule", "rated_by"]
    ordering_fields = ["rated_at", "created_at"]
    ordering = ["-rated_at"]

    def get_queryset(self):
        """Return exam results with related application and schedule context."""

        return ExamResult.objects.select_related(
            "application",
            "application__applicant",
            "exam_schedule",
            "rated_by",
        )

    def perform_create(self, serializer):
        """Set result evaluator and timestamp on creation."""

        serializer.save(rated_by=self.request.user, rated_at=timezone.now())


class InterviewScheduleViewSet(BaseRecruitmentViewSet):
    """CRUD viewset for interview schedules and panel assignments."""

    serializer_class = InterviewScheduleSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filterset_fields = ["job_posting", "interview_date"]
    ordering_fields = ["interview_date", "interview_time", "created_at"]
    ordering = ["interview_date", "interview_time"]

    def get_queryset(self):
        """Return interview schedules with posting, creator, and panel members."""

        return InterviewSchedule.objects.select_related(
            "job_posting",
            "created_by",
        ).prefetch_related("panel_members")

    def perform_create(self, serializer):
        """Set creator on interview schedule creation."""

        serializer.save(created_by=self.request.user)


class InterviewResultViewSet(BaseRecruitmentViewSet):
    """CRUD viewset for interview scoring outcomes."""

    serializer_class = InterviewResultSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filterset_fields = ["application", "interview_schedule", "rated_by"]
    ordering_fields = ["rated_at", "created_at"]
    ordering = ["-rated_at"]

    def get_queryset(self):
        """Return interview results with related app/schedule evaluator context."""

        return InterviewResult.objects.select_related(
            "application",
            "application__applicant",
            "interview_schedule",
            "rated_by",
        )

    def perform_create(self, serializer):
        """Set evaluator and timestamp on interview result creation."""

        serializer.save(rated_by=self.request.user, rated_at=timezone.now())


class RankingListViewSet(BaseRecruitmentViewSet):
    """Manage ranking lists and automated ranking entry generation."""

    serializer_class = RankingListSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filterset_fields = ["job_posting", "is_final"]
    ordering_fields = ["generated_at", "created_at"]
    ordering = ["-generated_at"]

    def get_queryset(self):
        """Return ranking lists with fully prefetched entries for API responses."""

        entry_qs = RankingEntry.objects.select_related("application", "application__applicant")
        return RankingList.objects.select_related("job_posting", "generated_by").prefetch_related(
            Prefetch("entries", queryset=entry_qs)
        )

    def perform_create(self, serializer):
        """Set generating user for manually created ranking lists."""

        serializer.save(generated_by=self.request.user, generated_at=timezone.now())

    def perform_update(self, serializer):
        """Block modifications once ranking list is finalized."""

        if serializer.instance.is_final:
            raise PermissionDenied("Finalized ranking lists cannot be modified.")
        serializer.save()

    def perform_destroy(self, instance):
        """Block deletion once ranking list is finalized."""

        if instance.is_final:
            raise PermissionDenied("Finalized ranking lists cannot be deleted.")
        instance.delete()

    @action(detail=False, methods=["post"], url_path="generate-ranking")
    def generate_ranking(self, request):
        """Generate ranking entries from complete exam and interview results."""

        job_posting_id = request.data.get("job_posting_id")
        if not job_posting_id:
            return error_response(
                "job_posting_id is required.",
                "missing_job_posting_id",
                field_errors={"job_posting_id": ["This field is required."]},
            )

        job_posting = JobPosting.objects.filter(pk=job_posting_id).first()
        if not job_posting:
            return error_response(
                "Job posting not found.",
                "job_posting_not_found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        applications = list(
            Application.objects.filter(job_posting_id=job_posting_id)
            .exclude(application_status=Application.ApplicationStatus.WITHDRAWN)
            .select_related("applicant")
            .prefetch_related(
                Prefetch("exam_results", queryset=ExamResult.objects.order_by("-rated_at")),
                Prefetch("interview_results", queryset=InterviewResult.objects.order_by("-rated_at")),
            )
        )

        if not applications:
            return error_response("No active applications found for this posting.", "no_applications")

        rows = []
        missing_exam = []
        missing_interview = []

        for application in applications:
            exam_result = next(iter(application.exam_results.all()), None)
            interview_result = next(iter(application.interview_results.all()), None)

            if not exam_result:
                missing_exam.append(application.id)
                continue
            if not interview_result:
                missing_interview.append(application.id)
                continue

            exam_score = Decimal(exam_result.total_score)
            interview_score = Decimal(interview_result.total_score)
            total_score = ((exam_score + interview_score) / Decimal("2")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            rows.append(
                {
                    "application": application,
                    "exam_score": exam_score,
                    "interview_score": interview_score,
                    "total_score": total_score,
                }
            )

        if missing_exam or missing_interview:
            return error_response(
                "Cannot generate ranking list; some applications have incomplete results.",
                "incomplete_results",
                field_errors={
                    "missing_exam_results": missing_exam,
                    "missing_interview_results": missing_interview,
                },
            )

        rows.sort(key=lambda item: item["total_score"], reverse=True)

        with transaction.atomic():
            ranking_list = RankingList.objects.create(
                job_posting=job_posting,
                generated_by=request.user,
                generated_at=timezone.now(),
            )
            entries = []
            for idx, row in enumerate(rows, start=1):
                entries.append(
                    RankingEntry(
                        ranking_list=ranking_list,
                        application=row["application"],
                        exam_score=row["exam_score"],
                        interview_score=row["interview_score"],
                        total_score=row["total_score"],
                        rank_number=idx,
                        is_recommended=idx <= job_posting.no_of_vacancies,
                    )
                )
            RankingEntry.objects.bulk_create(entries)

        serializer = self.get_serializer(ranking_list)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="finalize")
    def finalize(self, request, pk=None):
        """Finalize ranking list to lock post-generation modifications."""

        ranking_list = self.get_object()
        if ranking_list.is_final:
            return error_response("Ranking list is already finalized.", "already_finalized")

        ranking_list.is_final = True
        ranking_list.save(update_fields=["is_final", "updated_at"])
        return Response(self.get_serializer(ranking_list).data, status=status.HTTP_200_OK)


class RankingEntryViewSet(BaseRecruitmentViewSet):
    """Manage ranking entries with protection for finalized lists."""

    serializer_class = RankingEntrySerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filterset_fields = ["ranking_list", "is_recommended", "rank_number"]
    ordering_fields = ["rank_number", "total_score", "created_at"]
    ordering = ["rank_number"]

    def get_queryset(self):
        """Return ranking entries with linked ranking list and application loaded."""

        return RankingEntry.objects.select_related(
            "ranking_list",
            "application",
            "application__applicant",
        )

    def perform_create(self, serializer):
        """Prevent manual entry creation for finalized ranking lists."""

        ranking_list = serializer.validated_data["ranking_list"]
        if ranking_list.is_final:
            raise PermissionDenied("Cannot add entries to a finalized ranking list.")
        serializer.save()

    def perform_update(self, serializer):
        """Prevent manual entry updates for finalized ranking lists."""

        ranking_list = serializer.instance.ranking_list
        if ranking_list.is_final:
            raise PermissionDenied("Cannot edit entries in a finalized ranking list.")
        serializer.save()

    def perform_destroy(self, instance):
        """Prevent manual entry deletion for finalized ranking lists."""

        if instance.ranking_list.is_final:
            raise PermissionDenied("Cannot delete entries from a finalized ranking list.")
        instance.delete()


class AppointmentViewSet(BaseRecruitmentViewSet):
    """Manage appointment issuance, restricted to HR head/admin roles."""

    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated, IsHRHeadOrAdmin]
    filterset_fields = ["appointment_type", "effectivity_date"]
    ordering_fields = ["issued_at", "effectivity_date", "created_at"]
    ordering = ["-issued_at"]

    def get_queryset(self):
        """Return appointments with linked application and issuer preloaded."""

        return Appointment.objects.select_related(
            "application",
            "application__applicant",
            "issued_by",
        )

    def perform_create(self, serializer):
        """Set issuer and issue timestamp on appointment creation."""

        serializer.save(issued_by=self.request.user, issued_at=timezone.now())
