# Environment preparation

`setup.py` restores pinned local tools; `--install-runtime` additionally installs exact direct Debian 13 runtime packages and requires root. `startup_check.py` checks presence; `--emulators` performs actual emulator checks using separately supplied local Falling NES/CHR fixture files and a private A1200 Kickstart. These inputs are not included in the public repository; the main README documents the required locations.

The optional Docker scripts prepare and check local container isolation. They do not publish a Codex environment. The offline route requires an already prepared compatible host and does not fetch missing runtime packages. No runtime executable, container image, firmware or package cache is included in this repository. Review scripts and runtime requirements for your environment before running them.
