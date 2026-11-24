"""Email addresses are stored and compared lowercased; inputs are lowercased on entry."""

import pytest
from pydantic import ValidationError

from src.auth.schemas import LocalLoginRequest
from src.school.schemas import (
    ProvisionStudentRequest,
    ProvisionTeacherRequest,
    StudentEnrolmentEntry,
    TeacherInviteRequest,
)

_MIXED = "Chnsuri@Gmail.COM"


def test_local_login_lowercases_email():
    req = LocalLoginRequest(email=_MIXED, password="x")
    assert req.email == "chnsuri@gmail.com"


def test_teacher_invite_lowercases_email():
    req = TeacherInviteRequest(name="T", email=_MIXED)
    assert req.email == "chnsuri@gmail.com"


def test_provision_teacher_lowercases_email():
    req = ProvisionTeacherRequest(name="T", email=_MIXED)
    assert req.email == "chnsuri@gmail.com"


def test_provision_student_lowercases_email():
    req = ProvisionStudentRequest(name="S", email=_MIXED, grade=8)
    assert req.email == "chnsuri@gmail.com"


def test_enrolment_entry_lowercases_email():
    req = StudentEnrolmentEntry(email=_MIXED)
    assert req.email == "chnsuri@gmail.com"


def test_invalid_email_still_rejected():
    with pytest.raises(ValidationError):
        LocalLoginRequest(email="not-an-email", password="x")
