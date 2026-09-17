"""Tests for numerical regression diagnostics used by scientific validation."""

import numpy as np
import pytest

from surfs_up.core.regression import compare_arrays


def test_identical_outputs_pass():
    result = compare_arrays([1.0, 2.0, 3.0], [1.0, 2.0, 3.0], name="speed")
    assert result.passed
    assert result.max_abs_error == 0.0
    assert result.rms_error == 0.0


def test_small_solver_difference_passes_tolerance():
    result = compare_arrays(
        [400.0, 405.0, 410.0],
        [400.0001, 404.9999, 410.0001],
        rtol=1e-5,
        atol=1e-6,
        name="speed",
    )
    assert result.passed
    assert result.max_abs_error > 0
    assert result.max_relative_error > 0


def test_material_difference_fails_with_diagnostics():
    result = compare_arrays([1.0, 2.0], [1.0, 2.1], rtol=1e-6, atol=1e-9, name="density")
    assert not result.passed
    assert result.max_abs_error == pytest.approx(0.1)
    assert "density exceeds tolerance" in result.message


def test_shape_mismatch_is_not_broadcast():
    result = compare_arrays([1.0, 2.0], [[1.0, 2.0]], name="state")
    assert not result.passed
    assert "shape mismatch" in result.message


def test_nonfinite_values_are_rejected_when_locations_differ():
    result = compare_arrays([1.0, np.nan], [1.0, np.inf], name="state")
    assert not result.passed
    assert "non-finite" in result.message


def test_matching_nan_values_are_allowed():
    result = compare_arrays([1.0, np.nan], [1.0, np.nan], name="state")
    assert result.passed


def test_empty_arrays_are_valid():
    result = compare_arrays([], [], name="empty")
    assert result.passed
    assert result.size == 0
    assert result.max_abs_error == 0.0


def test_negative_tolerances_are_rejected():
    with pytest.raises(ValueError):
        compare_arrays([1.0], [1.0], rtol=-1e-6)
    with pytest.raises(ValueError):
        compare_arrays([1.0], [1.0], atol=-1e-9)
