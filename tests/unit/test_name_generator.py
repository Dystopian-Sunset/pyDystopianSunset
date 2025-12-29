"""Tests for name generation."""

import random
import pytest

from ds_common.name_generator import NameGenerator, Theme


class TestNameGenerator:
    """Test suite for NameGenerator class."""

    # Cyberpunk Theme Tests
    def test_generate_cyberpunk_channel_name_returns_string(self):
        """Test that generate_cyberpunk_channel_name returns a string."""
        name = NameGenerator.generate_cyberpunk_channel_name()
        assert isinstance(name, str)

    def test_generate_cyberpunk_channel_name_has_hyphen(self):
        """Test that generated names contain a hyphen separator."""
        name = NameGenerator.generate_cyberpunk_channel_name()
        assert "-" in name

    def test_generate_cyberpunk_channel_name_has_two_parts(self):
        """Test that generated names have exactly two parts (adjective-noun)."""
        name = NameGenerator.generate_cyberpunk_channel_name()
        parts = name.split("-")
        assert len(parts) == 2

    def test_generate_cyberpunk_channel_name_alliteration(self):
        """Test that generated names use alliteration (same first letter)."""
        random.seed(42)

        for _ in range(10):
            name = NameGenerator.generate_cyberpunk_channel_name()
            parts = name.split("-")
            assert len(parts) == 2
            adj, noun = parts
            assert adj[0] == noun[0], f"Expected alliteration in '{name}'"

    def test_generate_cyberpunk_channel_name_uses_valid_words(self):
        """Test that generated names use words from the dictionaries."""
        random.seed(123)
        name = NameGenerator.generate_cyberpunk_channel_name()
        parts = name.split("-")
        adj, noun = parts

        found_adj = False
        for letter_list in NameGenerator.cyberpunk_adjectives.values():
            if adj in letter_list:
                found_adj = True
                break
        assert found_adj, f"Adjective '{adj}' not found in adjectives dict"

        found_noun = False
        for letter_list in NameGenerator.cyberpunk_nouns.values():
            if noun in letter_list:
                found_noun = True
                break
        assert found_noun, f"Noun '{noun}' not found in nouns dict"

    # Fantasy Theme Tests
    def test_generate_fantasy_name_returns_string(self):
        """Test that generate_fantasy_name returns a string."""
        name = NameGenerator.generate_fantasy_name()
        assert isinstance(name, str)

    def test_generate_fantasy_name_has_hyphen(self):
        """Test that fantasy names contain a hyphen separator."""
        name = NameGenerator.generate_fantasy_name()
        assert "-" in name

    def test_generate_fantasy_name_has_two_parts(self):
        """Test that fantasy names have exactly two parts."""
        name = NameGenerator.generate_fantasy_name()
        parts = name.split("-")
        assert len(parts) == 2

    def test_generate_fantasy_name_alliteration(self):
        """Test that fantasy names use alliteration."""
        random.seed(42)

        for _ in range(10):
            name = NameGenerator.generate_fantasy_name()
            parts = name.split("-")
            assert len(parts) == 2
            adj, noun = parts
            assert adj[0] == noun[0], f"Expected alliteration in '{name}'"

    # Western Theme Tests
    def test_generate_western_name_returns_string(self):
        """Test that generate_western_name returns a string."""
        name = NameGenerator.generate_western_name()
        assert isinstance(name, str)

    def test_generate_western_name_has_hyphen(self):
        """Test that western names contain a hyphen separator."""
        name = NameGenerator.generate_western_name()
        assert "-" in name

    def test_generate_western_name_has_two_parts(self):
        """Test that western names have exactly two parts."""
        name = NameGenerator.generate_western_name()
        parts = name.split("-")
        assert len(parts) == 2

    def test_generate_western_name_alliteration(self):
        """Test that western names use alliteration."""
        random.seed(42)

        for _ in range(10):
            name = NameGenerator.generate_western_name()
            parts = name.split("-")
            assert len(parts) == 2
            adj, noun = parts
            assert adj[0] == noun[0], f"Expected alliteration in '{name}'"

    # Unified generate_name() Tests
    def test_generate_name_with_cyberpunk_theme(self):
        """Test generate_name with cyberpunk theme."""
        name = NameGenerator.generate_name(Theme.CYBERPUNK)
        assert isinstance(name, str)
        assert "-" in name

    def test_generate_name_with_fantasy_theme(self):
        """Test generate_name with fantasy theme."""
        name = NameGenerator.generate_name(Theme.FANTASY)
        assert isinstance(name, str)
        assert "-" in name

    def test_generate_name_with_western_theme(self):
        """Test generate_name with western theme."""
        name = NameGenerator.generate_name(Theme.WESTERN)
        assert isinstance(name, str)
        assert "-" in name

    def test_generate_name_default_is_cyberpunk(self):
        """Test that generate_name defaults to cyberpunk theme."""
        random.seed(42)
        cyberpunk_name = NameGenerator.generate_name(Theme.CYBERPUNK)

        random.seed(42)
        default_name = NameGenerator.generate_name()

        assert cyberpunk_name == default_name

    # Multiple Names Tests
    def test_generate_multiple_names_returns_list(self):
        """Test that generate_multiple_names returns a list."""
        names = NameGenerator.generate_multiple_names(5)
        assert isinstance(names, list)

    def test_generate_multiple_names_correct_count(self):
        """Test that generate_multiple_names returns the correct number of names."""
        count = 7
        names = NameGenerator.generate_multiple_names(count)
        assert len(names) == count

    def test_generate_multiple_names_default_count(self):
        """Test that generate_multiple_names defaults to 10 names."""
        names = NameGenerator.generate_multiple_names()
        assert len(names) == 10

    def test_generate_multiple_names_all_valid(self):
        """Test that all names from generate_multiple_names are valid."""
        names = NameGenerator.generate_multiple_names(5)

        for name in names:
            assert isinstance(name, str)
            assert "-" in name
            parts = name.split("-")
            assert len(parts) == 2

    def test_generate_multiple_names_with_fantasy_theme(self):
        """Test generating multiple fantasy names."""
        names = NameGenerator.generate_multiple_names(5, Theme.FANTASY)

        assert len(names) == 5
        for name in names:
            assert isinstance(name, str)
            assert "-" in name

    def test_generate_multiple_names_with_western_theme(self):
        """Test generating multiple western names."""
        names = NameGenerator.generate_multiple_names(5, Theme.WESTERN)

        assert len(names) == 5
        for name in names:
            assert isinstance(name, str)
            assert "-" in name

    # Dictionary Validation Tests
    def test_cyberpunk_adjectives_dict_has_all_letters(self):
        """Test that cyberpunk adjectives dictionary contains all 26 letters."""
        assert len(NameGenerator.cyberpunk_adjectives) == 26
        for letter in "abcdefghijklmnopqrstuvwxyz":
            assert letter in NameGenerator.cyberpunk_adjectives
            assert len(NameGenerator.cyberpunk_adjectives[letter]) > 0

    def test_cyberpunk_nouns_dict_has_all_letters(self):
        """Test that cyberpunk nouns dictionary contains all 26 letters."""
        assert len(NameGenerator.cyberpunk_nouns) == 26
        for letter in "abcdefghijklmnopqrstuvwxyz":
            assert letter in NameGenerator.cyberpunk_nouns
            assert len(NameGenerator.cyberpunk_nouns[letter]) > 0

    def test_fantasy_adjectives_dict_has_all_letters(self):
        """Test that fantasy adjectives dictionary contains all 26 letters."""
        assert len(NameGenerator.fantasy_adjectives) == 26
        for letter in "abcdefghijklmnopqrstuvwxyz":
            assert letter in NameGenerator.fantasy_adjectives
            assert len(NameGenerator.fantasy_adjectives[letter]) > 0

    def test_fantasy_nouns_dict_has_all_letters(self):
        """Test that fantasy nouns dictionary contains all 26 letters."""
        assert len(NameGenerator.fantasy_nouns) == 26
        for letter in "abcdefghijklmnopqrstuvwxyz":
            assert letter in NameGenerator.fantasy_nouns
            assert len(NameGenerator.fantasy_nouns[letter]) > 0

    def test_western_adjectives_dict_has_all_letters(self):
        """Test that western adjectives dictionary contains all 26 letters."""
        assert len(NameGenerator.western_adjectives) == 26
        for letter in "abcdefghijklmnopqrstuvwxyz":
            assert letter in NameGenerator.western_adjectives
            assert len(NameGenerator.western_adjectives[letter]) > 0

    def test_western_nouns_dict_has_all_letters(self):
        """Test that western nouns dictionary contains all 26 letters."""
        assert len(NameGenerator.western_nouns) == 26
        for letter in "abcdefghijklmnopqrstuvwxyz":
            assert letter in NameGenerator.western_nouns
            assert len(NameGenerator.western_nouns[letter]) > 0

    # Backward Compatibility Tests
    def test_adjectives_property_returns_cyberpunk(self):
        """Test that adjectives property returns cyberpunk adjectives for backward compatibility."""
        gen = NameGenerator()
        assert gen.adjectives == NameGenerator.cyberpunk_adjectives

    def test_nouns_property_returns_cyberpunk(self):
        """Test that nouns property returns cyberpunk nouns for backward compatibility."""
        gen = NameGenerator()
        assert gen.nouns == NameGenerator.cyberpunk_nouns

    # Determinism Tests
    def test_generate_cyberpunk_channel_name_deterministic_with_seed(self):
        """Test that seeded random produces deterministic results."""
        random.seed(999)
        name1 = NameGenerator.generate_cyberpunk_channel_name()

        random.seed(999)
        name2 = NameGenerator.generate_cyberpunk_channel_name()

        assert name1 == name2

    def test_generate_fantasy_name_deterministic_with_seed(self):
        """Test that seeded random produces deterministic fantasy names."""
        random.seed(555)
        name1 = NameGenerator.generate_fantasy_name()

        random.seed(555)
        name2 = NameGenerator.generate_fantasy_name()

        assert name1 == name2

    def test_generate_western_name_deterministic_with_seed(self):
        """Test that seeded random produces deterministic western names."""
        random.seed(777)
        name1 = NameGenerator.generate_western_name()

        random.seed(777)
        name2 = NameGenerator.generate_western_name()

        assert name1 == name2

    # Variety Tests
    def test_generate_cyberpunk_channel_name_variety(self):
        """Test that generator produces variety (not always the same name)."""
        names = set(NameGenerator.generate_multiple_names(20, Theme.CYBERPUNK))
        assert len(names) > 1

    def test_generate_fantasy_name_variety(self):
        """Test that fantasy generator produces variety."""
        names = set(NameGenerator.generate_multiple_names(20, Theme.FANTASY))
        assert len(names) > 1

    def test_generate_western_name_variety(self):
        """Test that western generator produces variety."""
        names = set(NameGenerator.generate_multiple_names(20, Theme.WESTERN))
        assert len(names) > 1

    # No Hyphens in Words Tests
    def test_no_hyphens_in_words(self):
        """Test that no individual words contain hyphens (which breaks the format)."""
        # Check cyberpunk adjectives
        for letter, words in NameGenerator.cyberpunk_adjectives.items():
            for word in words:
                assert "-" not in word, f"Cyberpunk adjective '{word}' in letter '{letter}' contains hyphen"

        # Check cyberpunk nouns
        for letter, words in NameGenerator.cyberpunk_nouns.items():
            for word in words:
                assert "-" not in word, f"Cyberpunk noun '{word}' in letter '{letter}' contains hyphen"

        # Check fantasy adjectives
        for letter, words in NameGenerator.fantasy_adjectives.items():
            for word in words:
                assert "-" not in word, f"Fantasy adjective '{word}' in letter '{letter}' contains hyphen"

        # Check fantasy nouns
        for letter, words in NameGenerator.fantasy_nouns.items():
            for word in words:
                assert "-" not in word, f"Fantasy noun '{word}' in letter '{letter}' contains hyphen"

        # Check western adjectives
        for letter, words in NameGenerator.western_adjectives.items():
            for word in words:
                assert "-" not in word, f"Western adjective '{word}' in letter '{letter}' contains hyphen"

        # Check western nouns
        for letter, words in NameGenerator.western_nouns.items():
            for word in words:
                assert "-" not in word, f"Western noun '{word}' in letter '{letter}' contains hyphen"

    # Theme Examples Test
    def test_different_themes_produce_different_names(self):
        """Test that different themes produce thematically different names (sampling)."""
        random.seed(123)
        cyberpunk_names = set(NameGenerator.generate_multiple_names(50, Theme.CYBERPUNK))

        random.seed(123)
        fantasy_names = set(NameGenerator.generate_multiple_names(50, Theme.FANTASY))

        random.seed(123)
        western_names = set(NameGenerator.generate_multiple_names(50, Theme.WESTERN))

        # The sets should be mostly different (themes use different word lists)
        # There might be a tiny overlap if words exist in multiple themes, but should be minimal
        overlap_cyber_fantasy = cyberpunk_names & fantasy_names
        overlap_cyber_western = cyberpunk_names & western_names
        overlap_fantasy_western = fantasy_names & western_names

        # Expect very few or no overlaps
        assert len(overlap_cyber_fantasy) < 5, "Too much overlap between cyberpunk and fantasy"
        assert len(overlap_cyber_western) < 5, "Too much overlap between cyberpunk and western"
        assert len(overlap_fantasy_western) < 5, "Too much overlap between fantasy and western"
