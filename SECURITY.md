# Security

## Design Principles

- All processing is local. No data leaves the machine.
- No network services are opened.
- No external API calls are made during normal operation.
- No telemetry or analytics.

## Safe Operations

- File paths are validated to prevent path traversal.
- Temporary files are created in system-controlled temp directories.
- Blender is launched as a controlled subprocess with timeout.
- Model files are loaded from the configured models directory only.
- Model checksums should be verified (when available).

## Safe Serialization

- Project files use JSON (safe format).
- No `pickle.load()` on untrusted data.
- Model files (.pt) are loaded with `torch.load` with weights_only=True where applicable.

## Reporting

Security issues should be reported through the project's issue tracker.
