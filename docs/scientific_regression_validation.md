# Scientific regression validation

SURFs_UP can launch SURF runs through both ordinary and chunked execution paths.
For numerical model development, a useful regression check is not only whether
a run completes, but whether two execution strategies produce scientifically
consistent outputs.

The `surfs_up.core.regression.compare_arrays` helper provides a small,
solver-independent comparison primitive for this purpose. It reports:

- maximum absolute error;
- maximum relative error;
- RMS error;
- sample count; and
- an explicit pass/fail message.

It intentionally refuses shape mismatches and non-matching non-finite values.
This avoids accidental NumPy broadcasting hiding a change in model output.
Matching NaNs are retained as equivalent so missing values do not automatically
turn an otherwise valid comparison into a failure.

## Recommended use

For a continuous-versus-chunked validation, compare the same physical output at
matching timestamps:

```python
from surfs_up.core.regression import compare_arrays

result = compare_arrays(
    continuous_speed,
    chunked_speed,
    rtol=1e-6,
    atol=1e-9,
    name="solar-wind speed",
)

assert result.passed, result.message
```

The tolerances should be selected from the numerical precision and expected
solver sensitivity of the specific SURF configuration, rather than treated as
universal scientific constants.

This layer is deliberately separate from the SURF solver. It can therefore be
used for continuous/chunked comparisons, restart checks, and cached/uncached
comparisons without coupling SURFs_UP to SURF's internal model representation.
