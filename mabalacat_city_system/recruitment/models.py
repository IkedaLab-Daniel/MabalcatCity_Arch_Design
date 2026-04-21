"""Database models for the recruitment app."""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """Abstract base model that adds created/updated audit timestamps."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class JobPosting(TimeStampedModel):
    """Represents an open position published by HR for recruitment."""

    class EmploymentType(models.TextChoices):
        PERMANENT = "PERMANENT", "Permanent"
        CASUAL = "CASUAL", "Casual"
        CONTRACTUAL = "CONTRACTUAL", "Contractual"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        CLOSED = "CLOSED", "Closed"
        CANCELLED = "CANCELLED", "Cancelled"

    title = models.CharField(max_length=255)
    position_code = models.ForeignKey(
        "hr_records.Position",
        on_delete=models.PROTECT,
        related_name="job_postings",
    )
    department = models.ForeignKey(
        "hr_records.Department",
        on_delete=models.PROTECT,
        related_name="job_postings",
    )
    employment_type = models.CharField(max_length=20, choices=EmploymentType.choices)
    salary_grade = models.PositiveSmallIntegerField()
    plantilla_item_no = models.CharField(max_length=100, blank=True)
    no_of_vacancies = models.PositiveIntegerField(default=1)
    qualification_standards = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.OPEN)
    date_posted = models.DateTimeField(default=timezone.now)
    deadline = models.DateTimeField()
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="posted_job_postings",
    )

    class Meta:
        ordering = ["-date_posted"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["department"]),
            models.Index(fields=["employment_type"]),
            models.Index(fields=["salary_grade"]),
            models.Index(fields=["date_posted"]),
            models.Index(fields=["deadline"]),
        ]

    def __str__(self) -> str:
        """Return a concise readable job posting label."""

        return f"{self.title} ({self.position_code})"


class Applicant(TimeStampedModel):
    """Stores applicant profile and eligibility details."""

    class Eligibility(models.TextChoices):
        CSE_PROFESSIONAL = "CSE_PROFESSIONAL", "CSE Professional"
        CSE_SUBPROFESSIONAL = "CSE_SUBPROFESSIONAL", "CSE Subprofessional"
        BAR = "BAR", "Bar"
        BOARD = "BOARD", "Board"
        NONE = "NONE", "None"

    last_name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    suffix = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=30)
    civil_status = models.CharField(max_length=30)
    address = models.TextField()
    contact_number = models.CharField(max_length=30)
    email = models.EmailField(unique=True)
    highest_education = models.CharField(max_length=255)
    school = models.CharField(max_length=255)
    eligibility = models.CharField(max_length=25, choices=Eligibility.choices, default=Eligibility.NONE)
    eligibility_rating = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    eligibility_date = models.DateField(null=True, blank=True)
    is_pwd = models.BooleanField(default=False)
    is_solo_parent = models.BooleanField(default=False)
    is_ips = models.BooleanField(default=False)

    class Meta:
        ordering = ["last_name", "first_name"]
        indexes = [
            models.Index(fields=["last_name", "first_name"]),
            models.Index(fields=["email"]),
            models.Index(fields=["eligibility"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        """Return applicant name in Last, First format."""

        parts = [self.last_name + ",", self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        if self.suffix:
            parts.append(self.suffix)
        return " ".join(parts)


class Application(TimeStampedModel):
    """Tracks an applicant's application to a specific posting."""

    class ApplicationStatus(models.TextChoices):
        RECEIVED = "RECEIVED", "Received"
        SHORTLISTED = "SHORTLISTED", "Shortlisted"
        EXAM_SCHEDULED = "EXAM_SCHEDULED", "Exam Scheduled"
        EXAM_DONE = "EXAM_DONE", "Exam Done"
        INTERVIEW_SCHEDULED = "INTERVIEW_SCHEDULED", "Interview Scheduled"
        INTERVIEW_DONE = "INTERVIEW_DONE", "Interview Done"
        FOR_DELIBERATION = "FOR_DELIBERATION", "For Deliberation"
        PASSED = "PASSED", "Passed"
        FAILED = "FAILED", "Failed"
        HIRED = "HIRED", "Hired"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"

    applicant = models.ForeignKey(
        Applicant,
        on_delete=models.CASCADE,
        related_name="applications",
    )
    job_posting = models.ForeignKey(
        JobPosting,
        on_delete=models.CASCADE,
        related_name="applications",
    )
    date_applied = models.DateTimeField(default=timezone.now)
    application_status = models.CharField(
        max_length=25,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.RECEIVED,
    )
    remarks = models.TextField(blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processed_recruitment_applications",
    )

    class Meta:
        ordering = ["-date_applied"]
        constraints = [
            models.UniqueConstraint(
                fields=["applicant", "job_posting"],
                name="uniq_application_per_posting",
            )
        ]
        indexes = [
            models.Index(fields=["application_status"]),
            models.Index(fields=["job_posting"]),
            models.Index(fields=["date_applied"]),
            models.Index(fields=["applicant"]),
        ]

    def __str__(self) -> str:
        """Return readable application identity."""

        return f"{self.applicant} - {self.job_posting.title}"


class ApplicationDocument(TimeStampedModel):
    """Uploaded documentary requirements tied to an application."""

    class DocumentType(models.TextChoices):
        RESUME = "RESUME", "Resume"
        PDS = "PDS", "Personal Data Sheet"
        TOR = "TOR", "Transcript of Records"
        CERT_ELIGIBILITY = "CERT_ELIGIBILITY", "Certificate of Eligibility"
        CERT_EMPLOYMENT = "CERT_EMPLOYMENT", "Certificate of Employment"
        NBI = "NBI", "NBI Clearance"
        BIRTH_CERT = "BIRTH_CERT", "Birth Certificate"
        OTHER = "OTHER", "Other"

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    file = models.FileField(upload_to="recruitment/documents/%Y/%m/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_application_documents",
    )

    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["document_type"]),
            models.Index(fields=["is_verified"]),
            models.Index(fields=["uploaded_at"]),
        ]

    def __str__(self) -> str:
        """Return readable document label."""

        return f"{self.application_id} - {self.document_type}"


class ExamSchedule(TimeStampedModel):
    """Exam schedule details for a specific job posting."""

    job_posting = models.ForeignKey(
        JobPosting,
        on_delete=models.CASCADE,
        related_name="exam_schedules",
    )
    exam_date = models.DateField()
    exam_time = models.TimeField()
    venue = models.CharField(max_length=255)
    instructions = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_exam_schedules",
    )

    class Meta:
        ordering = ["exam_date", "exam_time"]
        indexes = [
            models.Index(fields=["job_posting"]),
            models.Index(fields=["exam_date"]),
        ]

    def __str__(self) -> str:
        """Return concise exam schedule label."""

        return f"{self.job_posting.title} - {self.exam_date}"


class ExamResult(TimeStampedModel):
    """Scores and remarks from applicant examination phase."""

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="exam_results",
    )
    exam_schedule = models.ForeignKey(
        ExamSchedule,
        on_delete=models.CASCADE,
        related_name="results",
    )
    written_score = models.DecimalField(max_digits=6, decimal_places=2)
    oral_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    remarks = models.TextField(blank=True)
    rated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="rated_exam_results",
    )
    rated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-rated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["application", "exam_schedule"],
                name="uniq_exam_result_per_schedule",
            )
        ]
        indexes = [
            models.Index(fields=["application"]),
            models.Index(fields=["exam_schedule"]),
            models.Index(fields=["rated_at"]),
        ]

    @property
    def total_score(self) -> Decimal:
        """Compute weighted score with 70/30 written-to-oral ratio."""

        oral = self.oral_score or Decimal("0")
        return (self.written_score * Decimal("0.70")) + (oral * Decimal("0.30"))

    def __str__(self) -> str:
        """Return concise exam result label."""

        return f"ExamResult #{self.pk} for Application #{self.application_id}"


class InterviewSchedule(TimeStampedModel):
    """Interview schedule and panel assignments for a posting."""

    job_posting = models.ForeignKey(
        JobPosting,
        on_delete=models.CASCADE,
        related_name="interview_schedules",
    )
    interview_date = models.DateField()
    interview_time = models.TimeField()
    venue = models.CharField(max_length=255)
    panel_members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="interview_panels",
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_interview_schedules",
    )

    class Meta:
        ordering = ["interview_date", "interview_time"]
        indexes = [
            models.Index(fields=["job_posting"]),
            models.Index(fields=["interview_date"]),
        ]

    def __str__(self) -> str:
        """Return concise interview schedule label."""

        return f"{self.job_posting.title} - {self.interview_date}"


class InterviewResult(TimeStampedModel):
    """Captures interview scoring and evaluator remarks."""

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="interview_results",
    )
    interview_schedule = models.ForeignKey(
        InterviewSchedule,
        on_delete=models.CASCADE,
        related_name="results",
    )
    score = models.DecimalField(max_digits=6, decimal_places=2)
    behavioral_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    remarks = models.TextField(blank=True)
    rated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="rated_interview_results",
    )
    rated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-rated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["application", "interview_schedule"],
                name="uniq_interview_result_per_schedule",
            )
        ]
        indexes = [
            models.Index(fields=["application"]),
            models.Index(fields=["interview_schedule"]),
            models.Index(fields=["rated_at"]),
        ]

    @property
    def total_score(self) -> Decimal:
        """Compute weighted score with 70/30 technical-to-behavioral ratio."""

        behavioral = self.behavioral_score or Decimal("0")
        return (self.score * Decimal("0.70")) + (behavioral * Decimal("0.30"))

    def __str__(self) -> str:
        """Return concise interview result label."""

        return f"InterviewResult #{self.pk} for Application #{self.application_id}"


class RankingList(TimeStampedModel):
    """Container for generated ranking entries for a posting."""

    job_posting = models.ForeignKey(
        JobPosting,
        on_delete=models.CASCADE,
        related_name="ranking_lists",
    )
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="generated_ranking_lists",
    )
    generated_at = models.DateTimeField(default=timezone.now)
    is_final = models.BooleanField(default=False)

    class Meta:
        ordering = ["-generated_at"]
        indexes = [
            models.Index(fields=["job_posting"]),
            models.Index(fields=["is_final"]),
            models.Index(fields=["generated_at"]),
        ]

    def __str__(self) -> str:
        """Return concise ranking list label."""

        return f"RankingList #{self.pk} - {self.job_posting.title}"


class RankingEntry(TimeStampedModel):
    """Individual ranked entry under a ranking list."""

    ranking_list = models.ForeignKey(
        RankingList,
        on_delete=models.CASCADE,
        related_name="entries",
    )
    application = models.ForeignKey(
        Application,
        on_delete=models.PROTECT,
        related_name="ranking_entries",
    )
    exam_score = models.DecimalField(max_digits=6, decimal_places=2)
    interview_score = models.DecimalField(max_digits=6, decimal_places=2)
    performance_rating = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    total_score = models.DecimalField(max_digits=6, decimal_places=2)
    rank_number = models.PositiveIntegerField()
    is_recommended = models.BooleanField(default=False)

    class Meta:
        ordering = ["rank_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["ranking_list", "application"],
                name="uniq_application_per_ranking_list",
            ),
            models.UniqueConstraint(
                fields=["ranking_list", "rank_number"],
                name="uniq_rank_number_per_ranking_list",
            ),
        ]
        indexes = [
            models.Index(fields=["ranking_list"]),
            models.Index(fields=["rank_number"]),
            models.Index(fields=["total_score"]),
            models.Index(fields=["is_recommended"]),
        ]

    def __str__(self) -> str:
        """Return concise ranking entry label."""

        return f"#{self.rank_number} - Application #{self.application_id}"


class Appointment(TimeStampedModel):
    """Final appointment details for a hired application."""

    class AppointmentType(models.TextChoices):
        ORIGINAL = "ORIGINAL", "Original"
        PROMOTION = "PROMOTION", "Promotion"
        TRANSFER = "TRANSFER", "Transfer"
        REINSTATEMENT = "REINSTATEMENT", "Reinstatement"

    application = models.OneToOneField(
        Application,
        on_delete=models.PROTECT,
        related_name="appointment",
    )
    appointment_type = models.CharField(max_length=20, choices=AppointmentType.choices)
    effectivity_date = models.DateField()
    appointment_no = models.CharField(max_length=100, unique=True)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="issued_appointments",
    )
    issued_at = models.DateTimeField(default=timezone.now)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ["-issued_at"]
        indexes = [
            models.Index(fields=["appointment_type"]),
            models.Index(fields=["effectivity_date"]),
            models.Index(fields=["appointment_no"]),
            models.Index(fields=["issued_at"]),
        ]

    def __str__(self) -> str:
        """Return concise appointment label."""

        return f"{self.appointment_no} - {self.application}"
