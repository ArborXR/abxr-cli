"""Tests for MultipartFileS3 chunking math.

The byte-offset math is hard to spot-check when uploads work — corruption
manifests as failed S3 part assembly long after the test would have caught
it. These tests pin part-size calculation, part-count math, and seek/read
offsets by patching the size constants down so we can use tiny files.
"""

import os

import pytest

from abxr.multipart import MultipartFileS3


@pytest.fixture
def tiny_parts(mocker):
    """Shrink MIN_PART_SIZE so tests can use kilobyte-scale files."""
    mocker.patch.object(MultipartFileS3, "MIN_PART_SIZE", 1024)


def _write(tmp_path, name, content):
    f = tmp_path / name
    f.write_bytes(content)
    return f


class TestGetPartSize:
    def test_small_file_uses_min_part_size(self, tiny_parts, tmp_path):
        f = _write(tmp_path, "tiny.bin", b"x" * 100)
        assert MultipartFileS3(str(f)).part_size == 1024

    def test_medium_file_scales_with_size(self, tiny_parts, tmp_path):
        # MAX_PARTS = 1000, so a file of 1000 * 2048 bytes -> part_size = 2048
        f = _write(tmp_path, "med.bin", b"x" * (1000 * 2048))
        assert MultipartFileS3(str(f)).part_size == 2048

    def test_huge_file_clamps_at_max_part_size(self, mocker, tmp_path):
        # Patch both bounds down so we can exercise the upper clamp cheaply.
        mocker.patch.object(MultipartFileS3, "MIN_PART_SIZE", 512)
        mocker.patch.object(MultipartFileS3, "MAX_PART_SIZE", 2048)
        # size // MAX_PARTS would be 4096, but MAX_PART_SIZE clamps it to 2048
        f = _write(tmp_path, "huge.bin", b"x" * (1000 * 4096))
        assert MultipartFileS3(str(f)).part_size == 2048


class TestGetPartNumbers:
    def test_exact_multiple_of_part_size(self, tiny_parts, tmp_path):
        f = _write(tmp_path, "exact.bin", b"x" * (1024 * 3))
        assert MultipartFileS3(str(f)).get_part_numbers() == 3

    def test_one_byte_over_multiple_adds_a_part(self, tiny_parts, tmp_path):
        f = _write(tmp_path, "over.bin", b"x" * (1024 * 3 + 1))
        assert MultipartFileS3(str(f)).get_part_numbers() == 4

    def test_file_smaller_than_part_size_is_one_part(self, tiny_parts, tmp_path):
        f = _write(tmp_path, "small.bin", b"hello")
        assert MultipartFileS3(str(f)).get_part_numbers() == 1


class TestGetPart:
    def test_part_1_reads_from_offset_zero(self, tiny_parts, tmp_path):
        f = _write(tmp_path, "indexed.bin", b"A" * 1024 + b"B" * 1024 + b"C" * 1024)
        assert MultipartFileS3(str(f)).get_part(1) == b"A" * 1024

    def test_middle_part_reads_from_correct_offset(self, tiny_parts, tmp_path):
        f = _write(tmp_path, "indexed.bin", b"A" * 1024 + b"B" * 1024 + b"C" * 1024)
        assert MultipartFileS3(str(f)).get_part(2) == b"B" * 1024

    def test_final_part_is_truncated_to_remainder(self, tiny_parts, tmp_path):
        # 1024 + 1024 + 500 bytes -> 3 parts, last is 500 bytes
        f = _write(tmp_path, "remainder.bin", b"A" * 1024 + b"B" * 1024 + b"C" * 500)
        mp = MultipartFileS3(str(f))
        assert mp.get_part_numbers() == 3
        assert mp.get_part(3) == b"C" * 500

    def test_round_trip_concatenation_reproduces_file(self, tiny_parts, tmp_path):
        """Acid test: write a file, split into parts, concatenate -> original bytes."""
        content = os.urandom(5 * 1024 + 137)  # 5 full parts + 1 partial
        f = _write(tmp_path, "roundtrip.bin", content)
        mp = MultipartFileS3(str(f))
        reassembled = b"".join(mp.get_part(n) for n in range(1, mp.get_part_numbers() + 1))
        assert reassembled == content


class TestFileName:
    def test_extracts_basename_from_nested_path(self, tmp_path):
        nested = tmp_path / "sub" / "deep"
        nested.mkdir(parents=True)
        f = nested / "archive.zip"
        f.touch()
        assert MultipartFileS3(str(f)).file_name == "archive.zip"
