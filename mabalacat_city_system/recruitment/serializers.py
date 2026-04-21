"""Serializers for recruitment API resources."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from django.apps import apps
from django.utils import timezone
from rest_framework import serializers

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


def _get_hr_model(model_name: str):
    """Return HR model class by name from the hr_records app."""

    return apps.get_model("hr_records", model_name)


class ApplicantSerializer(serializers.ModelSerializer):
    """Serializer for applicant profiles with business-rule validations."""

    class Meta:
        model = Applicant
        fields = [
            "id",
            "last_name",
            "first_name",
            "middle_name",
            "suffix",
            "date_of_birth",
            "gender",
            "civil_status",
            "address",
            "contact_number",
            "email",
            "highest_education",
            "school",
            "eligibility",
            "eligibility_rating",
            "eligibility_date",
            "is_pwd",
            "is_solo_parent",
            "is_ips",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate_email(self, value: str) -> str:
        """Ensure applicant email remains unique across records."""

        queryset = Applicant.objects.filter(email__iexact=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("This email is already registered as an applicant.")
        return value

    def validate_date_of_birth(self, value: date) -> date:
        """Ensure applicant is at least 18 years old."""

        today = timezone.localdate()
        years = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
        if years < 18:
            raise serializers.ValidationError("Applicant must be at least 18 years old.")
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Validate conditional eligibility fields."""

        eligibility = attrs.get("eligibility", getattr(self.instance, "eligibility", Applicant.Eligibility.NONE))
        eligibility_rating = attrs.get("eligibility_rating", getattr(self.instance, "eligibility_rating", None))

        if eligibility != Applicant.Eligibility.NONE and eligibility_rating is None:
            raise serializers.ValidationError(
                {"eligibility_rating": "Eligibility rating is required when eligibility is not NONE."}
            )
        return attrs


class JobPostingSerializer(serializers.ModelSerializer):
    """Job posting serializer with nested read and flat write fields."""

    position_code = serializers.SerializerMethodField(read_only=True)
    department = serializers.SerializerMethodField(read_only=True)
    posted_by = serializers.SerializerMethodField(read_only=True)
    position_code_id = serializers.IntegerField(write_only=True)
    department_id = serializers.IntegerField(write_only=True)
    applications_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = JobPosting
        fields = [
            "id",
            "title",
            "position_code",
            "position_code_id",
            "department",
            "department_id",
            "employment_type",
            "salary_grade",
            "plantilla_item_no",
            "no_of_vacancies",
            "qualification_standards",
            "status",
            "date_posted",
            "deadline",
            "posted_by",
            "applications_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["status", "date_posted", "created_at", "updated_at"]

    def get_position_code(self, obj: JobPosting) -> dict[str, Any]:
        """Return nested position details for read operations."""

        return {
            "id": obj.position_code_id,
            "display": str(obj.position_code),
        }

    def get_department(self, obj: JobPosting) -> dict[str, Any]:
        """Return nested department details for read operations."""

        return {
            "id": obj.department_id,
            "display": str(obj.department),
        }

    def get_posted_by(self, obj: JobPosting) -> dict[str, Any]:
        """Return minimal posting user details."""

        user = obj.posted_by
        return {
            "id": user.pk,
            "username": getattr(user, "username", ""),
            "full_name": user.get_full_name() if hasattr(user, "get_full_name") else "",
        }

    def validate_position_code_id(self, value: int) -> int:
        """Ensure referenced position exists."""

        position_model = _get_hr_model("Position")
        if not position_model.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Selected position code does not exist.")
        return value

    def validate_department_id(self, value: int) -> int:
        """Ensure referenced department exists."""

        department_model = _get_hr_model("Department")
        if not department_model.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Selected department does not exist.")
        return value

    def _set_foreign_keys(self, validated_data: dict[str, Any]) -> dict[str, Any]:
        """Map flat write IDs to actual FK model instances."""

        position_id = validated_data.pop("position_code_id")
        department_id = validated_data.pop("department_id")

        position_model = _get_hr_model("Position")
        department_model = _get_hr_model("Department")

        validated_data["position_code"] = position_model.objects.get(pk=position_id)
        validated_data["department"] = department_model.objects.get(pk=department_id)
        return validated_data

    def create(self, validated_data: dict[str, Any]) -> JobPosting:
        """Create posting using flat ID write fields."""

        validated_data = self._set_foreign_keys(validated_data)
        return super().create(validated_data)

    def update(self, instance: JobPosting, validated_data: dict[str, Any]) -> JobPosting:
        """Update posting using flat ID write fields."""

        if "position_code_id" in validated_data and "department_id" in validated_data:
            validated_data = self._set_foreign_keys(validated_data)
        elif "position_code_id" in validated_data:
            position_model = _get_hr_model("Position")
            instance.position_code = position_model.objects.get(pk=validated_data.pop("position_code_id"))
        elif "department_id" in validated_data:
            department_model = _get_hr_model("Department")
            instance.department = department_model.objects.get(pk=validated_data.pop("department_id"))
        return super().update(instance, validated_data)


class ApplicationSerializer(serializers.ModelSerializer):
    """Serializer for applications with duplicate-submission checks."""

    applicant = ApplicantSerializer(read_only=True)
    applicant_id = serializers.PrimaryKeyRelatedField(
        source="applicant",
        queryset=Applicant.objects.all(),
        write_only=True,
    )

    class Meta:
        model = Application
        fields = [
            "id",
            "applicant",
            "applicant_id",
            "job_posting",
            "date_applied",
            "application_status",
            "remarks",
            "processed_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["date_applied", "application_status", "processed_by", "created_at", "updated_at"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Prevent duplicate applications per applicant per posting."""

        applicant = attrs.get("applicant", getattr(self.instance, "applicant", None))
        job_posting = attrs.get("job_posting", getattr(self.instance, "job_posting", None))

        if applicant and job_posting:
            duplicate_qs = Application.objects.filter(applicant=applicant, job_posting=job_posting)
            if self.instance:
                duplicate_qs = duplicate_qs.exclude(pk=self.instance.pk)
            if duplicate_qs.exists():
                raise serializers.ValidationError(
                    {"non_field_errors": ["Applicant already has an application for this posting."]}
                )
        return attrs


class ApplicationDocumentSerializer(serializers.ModelSerializer):
    """Serializer for application document uploads and verification metadata."""

    class Meta:
        model = ApplicationDocument
        fields = [
            "id",
            "application",
            "document_type",
            "file",
            "uploaded_at",
            "is_verified",
            "verified_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["uploaded_at", "verified_by", "created_at", "updated_at"]

    def validate_file(self, value):
        """Enforce upload constraints on file size and extension."""

        max_size = 5 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("File size must not exceed 5MB.")

        allowed_suffixes = {".pdf", ".jpg", ".jpeg", ".png"}
        suffix = Path(value.name).suffix.lower()
        if suffix not in allowed_suffixes:
            raise serializers.ValidationError("Unsupported file type. Allowed: PDF, JPG, PNG.")
        return value


class ExamScheduleSerializer(serializers.ModelSerializer):
    """Serializer for exam schedules."""

    class Meta:
        model = ExamSchedule
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]


class ExamResultSerializer(serializers.ModelSerializer):
    """Serializer for exam results with computed weighted total score."""

    total_score = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ExamResult
        fields = [
            "id",
            "application",
            "exam_schedule",
            "written_score",
            "oral_score",
            "total_score",
            "remarks",
            "rated_by",
            "rated_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["rated_by", "rated_at", "created_at", "updated_at", "total_score"]

    def get_total_score(self, obj: ExamResult) -> Decimal:
        """Expose computed total score."""

        return obj.total_score

    def create(self, validated_data: dict[str, Any]) -> ExamResult:
        """Create exam result while preserving computed total behavior."""

        instance = super().create(validated_data)
        _ = instance.total_score
        return instance

    def update(self, instance: ExamResult, validated_data: dict[str, Any]) -> ExamResult:
        """Update exam result while preserving computed total behavior."""

        instance = super().update(instance, validated_data)
        _ = instance.total_score
        return instance


class InterviewScheduleSerializer(serializers.ModelSerializer):
    """Serializer for interview schedules."""

    class Meta:
        model = InterviewSchedule
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]


class InterviewResultSerializer(serializers.ModelSerializer):
    """Serializer for interview results with computed weighted score."""

    total_score = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = InterviewResult
        fields = [
            "id",
            "application",
            "interview_schedule",
            "score",
            "behavioral_score",
            "total_score",
            "remarks",
            "rated_by",
            "rated_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["rated_by", "rated_at", "created_at", "updated_at", "total_score"]

    def get_total_score(self, obj: InterviewResult) -> Decimal:
        """Expose computed interview total score."""

        return obj.total_score

    def create(self, validated_data: dict[str, Any]) -> InterviewResult:
        """Create interview result while preserving computed total behavior."""

        instance = super().create(validated_data)
        _ = instance.total_score
        return instance

    def update(self, instance: InterviewResult, validated_data: dict[str, Any]) -> InterviewResult:
        """Update interview result while preserving computed total behavior."""

        instance = super().update(instance, validated_data)
        _ = instance.total_score
        return instance


class RankingEntrySerializer(serializers.ModelSerializer):
    """Serializer for ranking entries with nested read and flat write fields."""

    application = ApplicationSerializer(read_only=True)
    application_id = serializers.PrimaryKeyRelatedField(
        source="application",
        queryset=Application.objects.all(),
        write_only=True,
        required=False,
    )

    class Meta:
        model = RankingEntry
        fields = [
            "id",
            "ranking_list",
            "application",
            "application_id",
            "exam_score",
            "interview_score",
            "performance_rating",
            "total_score",
            "rank_number",
            "is_recommended",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class RankingListSerializer(serializers.ModelSerializer):
    """Serializer for ranking lists with nested read-only entries."""

    entries = RankingEntrySerializer(many=True, read_only=True)

    class Meta:
        model = RankingList
        fields = [
            "id",
            "job_posting",
            "generated_by",
            "generated_at",
            "is_final",
            "entries",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["generated_by", "generated_at", "is_final", "entries", "created_at", "updated_at"]


class AppointmentSerializer(serializers.ModelSerializer):
    """Serializer for finalized appointment records."""

    class Meta:
        model = Appointment
        fields = [
            "id",
            "application",
            "appointment_type",
            "effectivity_date",
            "appointment_no",
            "issued_by",
            "issued_at",
            "remarks",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["issued_by", "issued_at", "created_at", "updated_at"]
