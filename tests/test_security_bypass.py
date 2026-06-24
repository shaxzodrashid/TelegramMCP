from telegram_mcp.core.file_utils import is_suspicious, sanitize_filename


def test_is_suspicious_control_char_security_bypass_cases():
    # These payloads previously bypassed extension checks because the validator
    # examined the raw filename before the final filename sanitization step.
    malicious_files = [
        "evil.exe\x08",
        "evil.exe\u2002",
        "evil.exe\u200b",
        "evil.exe\x00",
        "evil.bat\n",
        "evil.sh\r",
    ]

    for filename in malicious_files:
        suspicious, ext = is_suspicious(filename)
        assert suspicious is True, f"Failed to detect {filename!r}"
        assert ext in {".exe", ".bat", ".sh"}

        sanitized = sanitize_filename(filename)
        assert sanitized in {"evil.exe", "evil.bat", "evil.sh"}, (
            f"Sanitization mismatch for {filename!r}"
        )


def test_is_suspicious_normalizes_control_char_malware_examples():
    # PR #69 specifically documented null-byte and newline examples.
    for filename in ["malware.exe\x00", "malware.exe\n"]:
        suspicious, ext = is_suspicious(filename)
        assert suspicious is True
        assert ext == ".exe"
        assert sanitize_filename(filename) == "malware.exe"
