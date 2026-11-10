# Locked Debian m68k recovery tools

On a compatible Debian 13 amd64 host with Python 3, curl, gpg, dpkg-deb and the Debian archive keyring:

```sh
python3 tools/recovery-m68k/setup.py
source tools/recovery-m68k/activate.sh
sh tools/recovery-m68k/smoke.sh
```

This extracts official packages locally; it does not install system packages or run maintainer scripts. The signed InRelease, package lock and provenance are retained. Setup verifies the release signature, signed package-index SHA256, and every package size/hash. It refuses silently changed versions. Downloaded packages and extracted executables remain ignored.

The tested versions are GCC 14.2.0, binutils 2.44 and QEMU 10.0.13. Existing static cross-compiler flags work. Dynamic Linux-m68k programs use `--sysroot="$AMIGA_M68K_TOOLCHAIN/root"` and QEMU `-L "$AMIGA_M68K_TOOLCHAIN/root/usr/m68k-linux-gnu"`. These Linux tests are not Amiga hardware tests.

The original recovery directory passed cached re-extraction and actual assemble/link/nm/objcopy/static/dynamic execution checks. These published scripts are byte-identical copies, with paths resolved relative to their own directory. Compatible native Debian runtime libraries remain a host prerequisite. Keep a private copy of package downloads for long-term reproducibility: current Debian mirrors may eventually retire these exact versions. No firmware or game cartridge is included.
