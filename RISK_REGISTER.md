# Risk Register

## Risks

| # | Risk | Likelihood | Impact | Mitigation | Status |
|---|---|---|---|---|---|
| R01 | PySide6 not available | Low | High | Install via pip/uv as part of setup | Open |
| R02 | Limited VRAM (8 GB) for ML inference | Medium | Medium | Use lightweight models; CPU fallback; monitor VRAM | Open |
| R03 | Blender subprocess management fragile | Medium | High | Use subprocess with timeout, logging, cleanup | Open |
| R04 | ONNX model compatibility | Low | Medium | Validate on target platform before finalizing | Open |
| R05 | Mannequin asset licensing | Medium | High | Verify all assets; create custom if needed | Open |
| R06 | CUDA out-of-memory during inference | Medium | Medium | Batch sizing; explicit memory management; fallback | Open |
| R07 | Windows path length issues | Low | Low | Long path support via registry; relative paths | Open |
| R08 | Unicode path handling | Low | Low | Use pathlib throughout; test with Unicode | Open |
| R09 | Model download failures | Low | Medium | Retry logic; checksum verification; manifest | Open |
| R10 | Packaging complexity (PySide6 + ML models) | High | High | PyInstaller testing; containerized build if needed | Open |
| R11 | Viewport backend selection failure | Medium | High | Technical spike before finalizing; fallback options | Open |
| R12 | 3D pose from monocular image ambiguity | High | Medium | User-guided depth; multiple hypotheses; IK constraints | Open |
| R13 | Application too complex for single build | Medium | High | Phased delivery; each phase usable independently | Open |
