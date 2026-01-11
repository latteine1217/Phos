# Deprecation Timeline

This document tracks deprecated functions and their planned removal dates.

## Philosophy

Following the **"Never Break Userspace"** principle:
- All deprecated functions remain functional (no immediate breakage)
- Deprecation warnings guide users to new implementations
- Minimum buffer period: 1 minor version (e.g., deprecated in v0.6.x, removed in v0.7.0)
- Migration path clearly documented

---

## Active Deprecations

### v0.6.4 → Remove in v0.7.0

| Function | Deprecated | Remove In | Replacement | Impact |
|----------|-----------|-----------|-------------|--------|
| `apply_bloom_mie_corrected()` | v0.6.4 (2026-01-12) | v0.7.0 | `apply_bloom(lux, bloom_params)` with `mode='mie_corrected'` | None (0 external callers) |

#### apply_bloom_mie_corrected()

**Location**: `Phos.py:1074`

**Reason**: Function refactored into `bloom_strategies.MieCorrectedBloomStrategy` for better maintainability and testability.

**Migration Guide**:
```python
# ❌ Old (deprecated)
result = apply_bloom_mie_corrected(lux, bloom_params, wavelength=550.0)

# ✅ New (recommended)
from bloom_strategies import apply_bloom

# Ensure bloom_params.mode = "mie_corrected"
result = apply_bloom(lux, bloom_params)
```

**Status**: 
- ✅ New implementation tested (21 tests, 100% pass)
- ✅ Deprecation warning added
- ✅ Backward compatibility maintained (function redirects to new implementation)
- ⏳ Scheduled removal: v0.7.0 (estimated 2026-Q1)

---

## Past Deprecations (Removed)

### v0.6.0 - Removed in v0.6.0

| Function | Deprecated | Removed | Replacement |
|----------|-----------|---------|-------------|
| `generate_grain_for_channel()` | v0.5.0 | v0.6.0 | `generate_grain()` |
| `generate_poisson_grain()` | v0.5.0 | v0.6.0 | `generate_grain()` with `mode='poisson'` |
| `apply_bloom_to_channel()` | v0.5.0 | v0.6.0 | `apply_bloom()` |

**See**: `BREAKING_CHANGES_v06.md` for migration details.

---

## Future Considerations (Not Yet Deprecated)

### Legacy Medium Physics Path

**Functions**: `apply_wavelength_bloom()`, `apply_bloom_with_psf()`  
**Location**: `Phos.py:730-820`  
**Status**: **Active (not deprecated)** - Used for backward compatibility with existing configs

**Reason to Keep**:
- Legacy medium physics mode (`wavelength_bloom_params.enabled=True`)
- Existing configurations may depend on this path
- Parallel execution path (not duplicated by new strategy pattern)

**Future Action**:
- Monitor usage in production
- Consider deprecation only if:
  1. No active users detected (telemetry shows 0 usage)
  2. All existing configs migrated to new physical mode
  3. At least 2 major versions notice period

---

## Deprecation Checklist

When deprecating a function, ensure:

- [ ] Add `@deprecated` decorator with clear reason and replacement
- [ ] Update function docstring with **DEPRECATED** notice
- [ ] Add entry to DEPRECATION_TIMELINE.md
- [ ] Update CHANGELOG.md (Deprecated section)
- [ ] Verify 0 breaking changes (tests still pass)
- [ ] Set removal version (next minor version)
- [ ] Add migration guide with code examples
- [ ] Search codebase for all callers (`rg "function_name\("`)
- [ ] Update documentation (if referenced in guides)

---

## Removal Checklist

When removing a deprecated function (in target version):

- [ ] Verify minimum buffer period elapsed (≥1 minor version)
- [ ] Confirm deprecation warning was visible to users
- [ ] Search codebase for remaining callers (should be 0)
- [ ] Remove function implementation
- [ ] Remove from DEPRECATION_TIMELINE.md (move to "Past Deprecations")
- [ ] Update CHANGELOG.md (Removed section)
- [ ] Update BREAKING_CHANGES_vXX.md
- [ ] Run full test suite (ensure no breakage)
- [ ] Update version number (minor bump: 0.6.x → 0.7.0)

---

## Reference

- **Deprecation Policy**: See `AGENTS.md` - Never Break Userspace principle
- **Version Strategy**: [Semantic Versioning 2.0.0](https://semver.org/)
- **Breaking Changes**: See `BREAKING_CHANGES_v06.md` for past examples

---

**Last Updated**: 2026-01-12  
**Next Review**: v0.7.0 release planning (2026-Q1)
