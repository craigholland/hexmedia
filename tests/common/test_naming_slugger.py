import string
from hexmedia.common.naming.slugger import random_slug


def test_random_slug_length_and_charset():
    slug = random_slug(12)
    assert len(slug) == 12
    for ch in slug:
        assert ch in string.ascii_lowercase


def test_random_slug_varies():
    # Not a cryptographic test; just ensure outputs usually differ.
    slugs = {random_slug(8) for _ in range(50)}
    assert len(slugs) > 40
