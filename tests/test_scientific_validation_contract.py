"""Contract tests for the public scientific validation API."""

import numpy as np

from surfs_up.core import RegressionResult, compare_arrays


def test_public_api_returns_structured_scientific_diagnostics():
    result = compare_arrays(
        np.array([400.0, 405.0, 410.0]),
        np.array([400.0, 405.000001, 410.0]),
        rtol=1e-6,
        atol=1e-9,
        name="speed",
    )

    assert isinstance(result, RegressionResult)
    assert result.size == 3
    assert result.max_abs_error > 0.0
    assert result.rms_error > 0.0
    assert result.passed is True


def test_public_api_rejects_nonmatching_infinite_outputs():
    result = compare_arrays(
        np.array([1.0, np.inf]),
        np.array([1.0, 2.0]),
        name="state",
    )

    assert result.passed is False
    assert "non-finite" in result.message


def test_public_api_preserves_nan_equivalence():
    result = compare_arrays(
        np.array([1.0, np.nan, 3.0]),
        np.array([1.0, np.nan, 3.0]),
        name="state",
    )

    assert result.passed is True
    assert result.size == 3
