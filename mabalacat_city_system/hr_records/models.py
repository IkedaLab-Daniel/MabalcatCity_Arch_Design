"""Core HR master-data models used by other apps."""

from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base model for audit timestamps."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Department(TimeStampedModel):
    """Organizational department reference model."""

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["name"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        """Return readable department label."""

        return f"{self.code} - {self.name}"


class Position(TimeStampedModel):
    """Position reference model for plantilla and hiring."""

    code = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="positions",
    )
    salary_grade = models.PositiveSmallIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["title"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["title"]),
            models.Index(fields=["department"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        """Return readable position label."""

        return f"{self.code} - {self.title}"
