# Release v0.3.2

No functional change to the image — equal to v0.3.1.

## Background

v0.3.2 was originally scoped to bring ffmpeg + chromium back into the image via
RPM Fusion free + EPEL. The wiring worked (EPEL and RPM Fusion repos install
correctly), but the actual packages have transitive deps that resolve only
against Red Hat paid entitlements (`librhsm-WARNING: Found 0 entitlement
certificates` is in effect for the langflow upstream image):

- `ffmpeg` (RPM Fusion free) needs `libSDL2-2.0.so.0()(64bit)`
- `chromium` (EPEL) needs `libpipewire-0.3.so.0()(64bit)`

Neither is reachable from UBI default, AppStream, CRB, or EPEL on a
subscription-less UBI 10 base. CRB IS enabled (`ubi-10-codeready-builder-rpms`
in repolist) but the missing libs are entitlement-gated and don't surface.

## What you get

Same as v0.3.1: Python, yt-dlp, Node 20, langflow, MiniMax registered as a
Global Model Provider. ffmpeg and chromium are NOT installed.

## Workarounds for ffmpeg / chromium users

Three options, none of them auto-installable in this Dockerfile today:

1. **Build on a RHEL-subscribed host** with entitlements (`librhsm` populated),
   so the UBI CRB/AppStream libs resolve. Then swap that image back into the
   stack. Requires a Red Hat Developer account or satellite subscription.
2. **Pin to langflow 1.10.0 (Debian base)** — keep the old Debian-style
   Dockerfile. Trades away 1.13+ langflow features and the registry-based
   MiniMax integration.
3. **Side-load ffmpeg / chromium binaries** at run-time (mount binaries or
   extract from a tarball). Doesn't get you automatic security updates.

None of these are small. v0.3.2 keeps the working v0.3.1 image and just
documents the gap. We can return to ffmpeg/chromium in a future release when
upstream langflow switches back to a Debian-flavoured base or ships its own
ffmpeg/chromium bundles.
