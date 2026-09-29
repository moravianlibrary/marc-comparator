"""The scheduler's account is not an account anyone administers.

Every periodic task runs on the system user's behalf, so it holds Admin. Nothing
stopped that being taken away — startup put it back, which made the damage last
until the next restart and leave no trace.
"""

from types import SimpleNamespace
from typing import Any, cast

import pytest

from access_control import service
from access_control.exceptions import SystemUserRoleModificationException
from entities.user import SYSTEM_USER_ID


class _User:
    def __init__(self, user_id, roles=None):
        self.id = user_id
        self.roles = roles if roles is not None else []
        self.saves = 0

    def save(self, _db, commit=True):  # noqa: FBT002
        self.saves += 1
        return self


def _patch(monkeypatch, user, role):
    monkeypatch.setattr(service.User, "get", classmethod(lambda cls, db, uid: user))
    monkeypatch.setattr(service.Role, "get", classmethod(lambda cls, db, rid: role))


NO_SESSION = cast(Any, object())


class TestTheSystemUserIsOffLimits:
    def test_its_role_cannot_be_taken_away(self, monkeypatch):
        admin = SimpleNamespace(name="Admin")
        user = _User(SYSTEM_USER_ID, roles=[admin])
        _patch(monkeypatch, user, admin)

        with pytest.raises(SystemUserRoleModificationException):
            service.unassign_role_from_user(str(SYSTEM_USER_ID), 1, NO_SESSION)

        assert user.roles == [admin], "the role was removed before the guard ran"
        assert user.saves == 0

    def test_it_cannot_be_given_another_one_either(self, monkeypatch):
        # Not a safety property so much as an honesty one: it already holds
        # every permission, so an edit here only looks like it did something.
        other = SimpleNamespace(name="Reviewer")
        user = _User(SYSTEM_USER_ID, roles=[])
        _patch(monkeypatch, user, other)

        with pytest.raises(SystemUserRoleModificationException):
            service.assign_role_to_user(str(SYSTEM_USER_ID), 2, NO_SESSION)

        assert user.roles == []

    def test_an_ordinary_user_is_unaffected(self, monkeypatch):
        import uuid

        role = SimpleNamespace(name="Reviewer")
        user = _User(uuid.uuid4(), roles=[])
        _patch(monkeypatch, user, role)

        service.assign_role_to_user(str(user.id), 2, NO_SESSION)

        assert user.roles == [role]


class TestAssigningTwiceIsNotAnError:
    def test_a_role_the_user_already_has_is_left_alone(self, monkeypatch):
        """``user_roles`` is keyed on (user_id, role_id).

        Appending a duplicate raised IntegrityError, which nothing in the app
        catches, so the endpoint answered 500 for an action whose desired end
        state was already true.
        """

        import uuid

        role = SimpleNamespace(name="Reviewer")
        user = _User(uuid.uuid4(), roles=[role])
        _patch(monkeypatch, user, role)

        service.assign_role_to_user(str(user.id), 2, NO_SESSION)

        assert user.roles == [role], "the role was appended a second time"

    def test_assign_and_unassign_agree_about_doing_nothing(self, monkeypatch):
        # Unassign has always been silent when there was nothing to remove.
        import uuid

        role = SimpleNamespace(name="Reviewer")
        user = _User(uuid.uuid4(), roles=[])
        _patch(monkeypatch, user, role)

        service.unassign_role_from_user(str(user.id), 2, NO_SESSION)

        assert user.roles == []
