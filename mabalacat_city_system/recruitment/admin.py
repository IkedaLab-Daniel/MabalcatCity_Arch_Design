"""Admin registrations for recruitment models."""

from django.contrib import admin

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


class RankingEntryInline(admin.TabularInline):
    """Inline display for ranking entries under a ranking list."""

    model = RankingEntry
    extra = 0
    fields = (
        "application",
        "exam_score",
        "interview_score",
        "performance_rating",
        "total_score",
        "rank_number",
        "is_recommended",
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    """Admin configuration for job postings."""

    list_display = (
        "title",
        "position_code",
        "department",
        "employment_type",
        "salary_grade",
        "status",
        "deadline",
        "no_of_vacancies",
        "posted_by",
        "date_posted",
    )
    list_filter = ("status", "employment_type", "department", "salary_grade")
    search_fields = ("title", "plantilla_item_no", "position_code__code", "position_code__title")
    ordering = ("-date_posted",)
    raw_id_fields = ("position_code", "department", "posted_by")


@admin.register(Applicant)
class ApplicantAdmin(admin.ModelAdmin):
    """Admin configuration for applicants."""

    list_display = (
        "last_name",
        "first_name",
        "middle_name",
        "email",
        "contact_number",
        "eligibility",
        "is_pwd",
        "is_solo_parent",
        "is_ips",
        "created_at",
    )
    list_filter = ("eligibility", "is_pwd", "is_solo_parent", "is_ips", "civil_status", "gender")
    search_fields = ("last_name", "first_name", "middle_name", "email", "contact_number")
    ordering = ("last_name", "first_name")


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    """Admin configuration for applications."""

    list_display = (
        "id",
        "applicant",
        "job_posting",
        "application_status",
        "date_applied",
        "processed_by",
    )
    list_filter = ("application_status", "job_posting", "date_applied")
    search_fields = (
        "applicant__last_name",
        "applicant__first_name",
        "applicant__email",
        "job_posting__title",
    )
    ordering = ("-date_applied",)
    raw_id_fields = ("applicant", "job_posting", "processed_by")


@admin.register(ApplicationDocument)
class ApplicationDocumentAdmin(admin.ModelAdmin):
    """Admin configuration for application documents."""

    list_display = (
        "id",
        "application",
        "document_type",
        "is_verified",
        "verified_by",
        "uploaded_at",
    )
    list_filter = ("document_type", "is_verified", "uploaded_at")
    search_fields = (
        "application__applicant__last_name",
        "application__applicant__first_name",
        "application__applicant__email",
    )
    ordering = ("-uploaded_at",)
    raw_id_fields = ("application", "verified_by")


@admin.register(ExamSchedule)
class ExamScheduleAdmin(admin.ModelAdmin):
    """Admin configuration for exam schedules."""

    list_display = ("job_posting", "exam_date", "exam_time", "venue", "created_by")
    list_filter = ("exam_date", "job_posting")
    search_fields = ("job_posting__title", "venue")
    ordering = ("exam_date", "exam_time")
    raw_id_fields = ("job_posting", "created_by")


@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    """Admin configuration for exam results."""

    list_display = (
        "id",
        "application",
        "exam_schedule",
        "written_score",
        "oral_score",
        "total_score",
        "rated_by",
        "rated_at",
    )
    list_filter = ("rated_at", "exam_schedule")
    search_fields = (
        "application__applicant__last_name",
        "application__applicant__first_name",
        "application__job_posting__title",
    )
    ordering = ("-rated_at",)
    raw_id_fields = ("application", "exam_schedule", "rated_by")


@admin.register(InterviewSchedule)
class InterviewScheduleAdmin(admin.ModelAdmin):
    """Admin configuration for interview schedules."""

    list_display = ("job_posting", "interview_date", "interview_time", "venue", "created_by")
    list_filter = ("interview_date", "job_posting")
    search_fields = ("job_posting__title", "venue")
    ordering = ("interview_date", "interview_time")
    raw_id_fields = ("job_posting", "created_by")
    filter_horizontal = ("panel_members",)


@admin.register(InterviewResult)
class InterviewResultAdmin(admin.ModelAdmin):
    """Admin configuration for interview results."""

    list_display = (
        "id",
        "application",
        "interview_schedule",
        "score",
        "behavioral_score",
        "total_score",
        "rated_by",
        "rated_at",
    )
    list_filter = ("rated_at", "interview_schedule")
    search_fields = (
        "application__applicant__last_name",
        "application__applicant__first_name",
        "application__job_posting__title",
    )
    ordering = ("-rated_at",)
    raw_id_fields = ("application", "interview_schedule", "rated_by")


@admin.register(RankingList)
class RankingListAdmin(admin.ModelAdmin):
    """Admin configuration for ranking lists."""

    list_display = ("id", "job_posting", "generated_by", "generated_at", "is_final")
    list_filter = ("is_final", "generated_at", "job_posting")
    search_fields = ("job_posting__title",)
    ordering = ("-generated_at",)
    raw_id_fields = ("job_posting", "generated_by")
    inlines = [RankingEntryInline]


@admin.register(RankingEntry)
class RankingEntryAdmin(admin.ModelAdmin):
    """Admin configuration for ranking entries."""

    list_display = (
        "ranking_list",
        "rank_number",
        "application",
        "exam_score",
        "interview_score",
        "performance_rating",
        "total_score",
        "is_recommended",
    )
    list_filter = ("is_recommended", "ranking_list")
    search_fields = (
        "application__applicant__last_name",
        "application__applicant__first_name",
        "application__job_posting__title",
    )
    ordering = ("ranking_list", "rank_number")
    raw_id_fields = ("ranking_list", "application")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    """Admin configuration for appointments."""

    list_display = (
        "appointment_no",
        "application",
        "appointment_type",
        "effectivity_date",
        "issued_by",
        "issued_at",
    )
    list_filter = ("appointment_type", "effectivity_date", "issued_at")
    search_fields = ("appointment_no", "application__applicant__last_name", "application__job_posting__title")
    ordering = ("-issued_at",)
    raw_id_fields = ("application", "issued_by")
