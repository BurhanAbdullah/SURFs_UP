"""Numerical regression helpers for validating SURF-derived results.

The helpers in this module deliberately operate on arrays rather than SURF's
model internals.  This keeps the validation layer usable for continuous vs.
chunked runs, restart comparisons, cached vs. uncached runs, and future SURF
output formats without coupling it to a particular solver implementation.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class RegressionResult:
    """Summary of a numerical comparison."""

    passed: bool
    max_abs_error: float
    max_relative_error: float
    rms_error: float
    size: int
    message: str


def compare_arrays(
    reference: object,
    candidate: object,
    *,
    rtol: float = 1e-6,
    atol: float = 1e-9,
    name: str = "array",
) -> RegressionResult:
    """Compare two numerical outputs with absolute and relative tolerances.

    ``numpy.allclose`` determines pass/fail, while the returned diagnostics
    make a failed scientific regression actionable.  Non-finite values are
    rejected unless they occur in exactly the same position and are both NaN.
    Shape mismatches are reported without attempting implicit broadcasting.
    """
    if rtol < 0 or atol < 0:
        raise ValueError("rtol and atol must be non-negative")

    ref = np.asarray(reference, dtype=float)
    got = np.asarray(candidate, dtype=float)

    if ref.shape != got.shape:
        return RegressionResult(
            passed=False,
            max_abs_error=float("inf"),
            max_relative_error=float("inf"),
            rms_error=float("inf"),
            size=ref.size,
            message=f"{name} shape mismatch: {ref.shape} != {got.shape}",
        )

    both_nan = np.isnan(ref) & np.isnan(got)
    finite = np.isfinite(ref) & np.isfinite(got)
    comparable = finite | both_nan

    if not np.all(comparable):
        bad = int(np.count_nonzero(~comparable))
        return RegressionResult(
            passed=False,
            max_abs_error=float("inf"),
            max_relative_error=float("inf"),
            rms_error=float("inf"),
            size=ref.size,
            message=f"{name} contains {bad} non-matching non-finite value(s)",
        )

    ref_f = ref[finite]
    got_f = got[finite]
    if ref_f.size:
        abs_error = np.abs(got_f - ref_f)
        max_abs = float(np.max(abs_error))
        scale = np.maximum(np.abs(ref_f), atol)
        max_rel = float(np.max(abs_error / scale))
        rms = float(np.sqrt(np.mean(np.square(got_f - ref_f))))
    else:
        max_abs = max_rel = rms = 0.0

    passed = bool(np.allclose(ref, got, rtol=rtol, atol=atol, equal_nan=True))
    if passed:
        message = f"{name} agrees within rtol={rtol:g}, atol={atol:g}"
    else:
        message = (
            f"{name} exceeds tolerance: max_abs={max_abs:.3e}, "
            f"max_rel={max_rel:.3e}, rms={rms:.3e}"
        )

    return RegressionResult(
        passed=passed,
        max_abs_error=max_abs,
        max_relative_error=max_rel,
        rms_error=rms,
        size=ref.size,
        message=message,
    )
