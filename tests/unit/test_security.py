"""Unit tests for app.core.security — JWT and password helpers."""

from datetime import timedelta

import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


class TestHashPassword:
    def test_returns_string(self) -> None:
        result = hash_password("secret")
        assert isinstance(result, str)

    def test_hashed_differs_from_plain(self) -> None:
        plain = "my_password"
        assert hash_password(plain) != plain

    def test_two_hashes_differ(self) -> None:
        # bcrypt generates a fresh salt each time
        assert hash_password("same") != hash_password("same")


class TestVerifyPassword:
    def test_correct_password_returns_true(self) -> None:
        plain = "correct_password"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_wrong_password_returns_false(self) -> None:
        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False

    def test_empty_password_fails(self) -> None:
        hashed = hash_password("notempty")
        assert verify_password("", hashed) is False


class TestCreateAccessToken:
    def test_returns_string(self) -> None:
        token = create_access_token("user-uuid")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_custom_expiry(self) -> None:
        token = create_access_token("user-uuid", expires_delta=timedelta(hours=1))
        assert isinstance(token, str)

    def test_different_subjects_produce_different_tokens(self) -> None:
        t1 = create_access_token("user-1")
        t2 = create_access_token("user-2")
        assert t1 != t2


class TestDecodeAccessToken:
    def test_valid_token_returns_subject(self) -> None:
        subject = "caregiver-abc-123"
        token = create_access_token(subject)
        result = decode_access_token(token)
        assert result == subject

    def test_invalid_token_returns_none(self) -> None:
        result = decode_access_token("not.a.valid.token")
        assert result is None

    def test_empty_string_returns_none(self) -> None:
        result = decode_access_token("")
        assert result is None

    def test_malformed_jwt_returns_none(self) -> None:
        result = decode_access_token("eyJhbGciOiJIUzI1NiJ9.garbage.sig")
        assert result is None

    def test_tampered_signature_returns_none(self) -> None:
        token = create_access_token("user-1")
        header, payload, _ = token.split(".")
        # Replace the entire signature with garbage
        tampered = f"{header}.{payload}.invalidsignatureXXXXXXX"
        assert decode_access_token(tampered) is None
