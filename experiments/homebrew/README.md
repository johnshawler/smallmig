# Falling movement slice

This is a limited native Amiga translation of selected Falling v1.1 ROM logic, not a complete conversion. It translates the movement entry at $C6C6 through $C753 and hands back to a native adapter at the original jump target $C7ED. Rendering, controller input and Paula feedback are native adaptations; full NES video/audio compatibility is not claimed.

The external MIT-licensed fixture comes from `xram64/falling-nes` commit `52dcb8a951200562e696dfc2aba5d4d14edd0078`. `references/falling/falling.nes` is 40,976 bytes and SHA-256 `e22b947542c2d7e595bf84725b333be7af8189c5965b9c53e356a249c7d79943`. Assembly source and the MIT notice are preserved. The NES and CHR binaries are not included in this public repository; supply them locally from that pinned upstream tree before running these optional tests. Adapter/model scripts retain their existing 0BSD notices.

Run all commands from the repository root. `python3 experiments/homebrew/build.py` prepares the host cases and builds native output. `python3 experiments/homebrew/run_mesen_reference.py` records a source-system reference. `python3 experiments/homebrew/run_test.py --with-mesen` runs reference and native checks after tools and private Kickstart are configured. Generated results stay under ignored `build/` and `evidence/` directories.
