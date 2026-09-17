# Scientific Validation Contribution

This document records the scientific-validation contribution to SURFs_UP and provides a reproducible pattern for checking numerical output changes.

## Contribution scope

The validation layer is intentionally solver-independent. It compares two numerical outputs without depending on SURF's internal model representation, making it suitable for continuous-versus-chunked runs, restart checks, and cached-versus-uncached comparisons.

The public helper is:

```python
from surfs_up.core.regression import compare_arrays
```

It reports:

- maximum absolute error;
- maximum relative error;
- RMS error;
- number of samples; and
- an explicit pass/fail result.

Shape mismatches are rejected rather than allowing implicit NumPy broadcasting. Non-finite values must match at the same locations; matching NaNs are accepted.

## Reproducible validation pattern

For a physical quantity evaluated at identical timestamps:

```python
result = compare_arrays(
    reference_output,
    candidate_output,
    rtol=1e-6,
    atol=1e-9,
    name="solar-wind speed",
)

if not result.passed:
    raise AssertionError(result.message)
```

Tolerances are configuration-dependent and should be justified from numerical precision and expected solver sensitivity. They are not universal scientific constants.

## Contribution and review checklist

Before accepting a change that can alter scientific outputs:

1. Compare the same physical quantity on the same sample/timestamp grid.
2. Confirm that array shapes agree.
3. Record absolute, relative, and RMS errors.
4. Check non-finite values explicitly.
5. Add a regression test for the affected behavior.
6. State the numerical invariant and tolerance in the pull request.
7. Keep unrelated refactoring out of the scientific fix.

This makes numerical changes reviewable and provides a durable regression record for future SURFs_UP development.
