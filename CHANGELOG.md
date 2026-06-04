# createrington-skin-api (Python)

This changelog tracks the Createrington Skin API Python SDK. A release publishes
to PyPI when a version bump is merged to `main`.

## v2.3.3

### Fixed

- Repository links in the package metadata now point to the public GitHub
  repository instead of the internal Gitea host.

## v2.3.2

### Changed

- Relicensed under Apache-2.0 (previously unlicensed). The public API is unchanged.
- The SDK now lives in its own open-source repository, and `_poses.py` is
  generated from the published OpenAPI document rather than from server-side files.
- Version aligned with the other Createrington Skin API SDKs (.NET, TypeScript)
  so all clients share one version line.

## v1.3.1

### Changed

- Boolean render params now serialize as `true`/`false` on the wire instead of
  `1`/`0` (`slim=true`, `outline=true`); `outline` is still omitted when off. The
  public API is unchanged and the server accepts both forms, so this is
  non-breaking.

## v1.3.0

### Added

- `render(..., outline=...)`: optional flag to draw an outline around the
  rendered skin. Defaults to off; when off the request omits the parameter so
  the render cache key for non-outline calls is unchanged. Additive and
  non-breaking.

## v1.2.0

### Added

- `Poses`: named constants for every pose known to the SDK (e.g. `Poses.wave`),
  for discoverability and autocompletion. This is the recommended way to
  reference a pose by name. Additive and non-breaking.

### Changed

- Docs now lead with `Poses`. `KNOWN_POSES` and `KnownPose` remain exported for
  iteration and validation.

## v1.1.0

### Added

- `random_pose()` returns a uniformly random pose name from `KNOWN_POSES`,
  typed as `KnownPose`. Additive and non-breaking.

## v1.0.1

### Fixed

- A server-provided `retryAfterMs` that was zero or negative no longer crashes
  the sync client (`time.sleep` rejects negative values); such values now fall
  through to the normal exponential backoff.

### Changed

- Cap how long a server-provided `retryAfterMs` can pause a retry (60s) so a
  misbehaving server cannot make the client hang. The original value is still
  reported on `SkinApiError.retry_after_ms`.
- Use builtin generic types (`tuple`, `type`) instead of the deprecated
  `typing.Tuple` / `typing.Type`.

## v1.0.0

Initial release on PyPI.

### Surface

- `SkinApiClient` (sync) and `AsyncSkinApiClient` (async), both backed by
  `httpx` and usable as context managers.
- `render(pose, *, uuid | username | skin_url | skin_base64 | png, slim,
  width, height)` returning PNG `bytes`. Exactly one skin source is required.
- `api_key` falls back to the `SKIN_API_KEY` environment variable; `base_url`
  defaults to `https://api.createrington.com`.
- `KNOWN_POSES` tuple + `KnownPose` literal type generated from the server's
  pose data; `render` still accepts any pose string.
- Single `SkinApiError` carrying `code`, `status`, and `retry_after_ms`.
  Server `UPPER_SNAKE` codes are normalized to the documented lowercase form.
- Retries `429`/`502`/`503`/`504` and network errors with exponential
  backoff, honouring `retryAfterMs` on `429`.
- Ships `py.typed` for full mypy/pyright inference.
