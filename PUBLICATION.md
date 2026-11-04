# Public source import validation

Checked on 2026-11-04 before publication:

- Python syntax: 20 files passed.
- Original 6502 probe: 131,072 host-model-versus-math cases passed, covering 13 instruction addresses.
- Falling movement model: 217,088 host-model-versus-math cases passed, covering 57 instruction addresses. The fresh source-only run generated 192 target fixtures; no historical Mesen traces were imported.
- Licensed Falling fixture SHA-256 and source/CHR correspondence passed through its host preparation checks. Its MIT license was independently checked at the pinned upstream commit.
- Local Docker source-context preparation passed; no Docker image was built for this import.
- Private archive fallback removed from `run.py`; users must explicitly provide `AMIGA_KICKSTART`. The source-context preparer no longer depends on a task-specific AGENTS file.
- Secret-pattern and publication inventory checks completed. Proprietary ROMs, generated output, runtime binaries, package caches and workspace logs are excluded. No NES ROM or CHR binary is published. Host-model validation used the existing licensed development fixture locally; binary fixtures are deliberately omitted from this public source import. Optional Falling tests therefore require separately supplied local inputs, with upstream identity and retained MIT notices documented.

Native compilation, FS-UAE, Mesen, graphics/audio/input, container isolation and Codex environment creation were not rerun in the publication workspace. Existing development results described in the README remain historical results, not proof that a newly provisioned environment is ready. No CI workflow or published environment is claimed.

Existing file-level licenses and upstream notices are preserved. No blanket license was invented for previously unlicensed files.
