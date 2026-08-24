import pytest

from slopo.indexing.parsing.registry import parser_profile_fingerprint


def test_parser_profile_rejects_unsupported_source_extension():
    with pytest.raises(ValueError, match=r"unsupported source extension '\.vue'"):
        parser_profile_fingerprint([".py", ".vue"])
