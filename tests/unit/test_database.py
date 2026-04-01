"""Unit tests for app.database — get_db generator behavior."""

import contextlib
from unittest.mock import MagicMock, patch


class TestGetDb:
    def test_yields_session_and_commits_on_success(self) -> None:
        from app.database import get_db

        mock_session = MagicMock()
        with patch("app.database.SessionLocal", return_value=mock_session):
            gen = get_db()
            session = next(gen)
            assert session is mock_session
            with contextlib.suppress(StopIteration):
                next(gen)
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    def test_rolls_back_and_reraises_on_exception(self) -> None:
        import pytest

        from app.database import get_db

        mock_session = MagicMock()
        with patch("app.database.SessionLocal", return_value=mock_session):
            gen = get_db()
            next(gen)
            with pytest.raises(RuntimeError):
                gen.throw(RuntimeError("DB failure"))

        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()
        mock_session.commit.assert_not_called()

    def test_always_closes_session(self) -> None:
        from app.database import get_db

        mock_session = MagicMock()
        with patch("app.database.SessionLocal", return_value=mock_session):
            gen = get_db()
            next(gen)
            with contextlib.suppress(StopIteration):
                next(gen)
        mock_session.close.assert_called_once()
