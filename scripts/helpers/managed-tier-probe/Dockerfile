# The OS-level managed tier, observable without root on the host.
#
# `/etc/claude-code/` needs root to write and the build sandbox has none, so the
# probe bind-mounts a prepared directory over that exact path INSIDE a container
# and runs the operator's real `claude` binary there. Nothing about the tier is
# simulated: the binary reads the same absolute path it reads on a real host.
#
# Non-root on purpose. `--dangerously-skip-permissions` refuses to run as root,
# and the fleet's dispatches do not run as root either.
#
# THE UID IS THE HOST USER'S, PASSED IN BY probe.sh — never a literal. The
# trial directories are bind-mounted from the host, owned by whoever runs the
# probe, and `~/.claude` among them is 0700: a container user with any other
# uid gets `Permission denied` before the first trial. A hardcoded 1001 ran
# clean on the host that wrote it and failed on the first uid-1000 host.
# `ubuntu:24.04` already ships a uid-1000 `ubuntu` user, so whatever holds the
# requested uid is removed first rather than colliding with `useradd`.
#
# `apt-get clean` rather than the usual `rm -rf /var/lib/apt/lists/*`: the
# fleet's own safety hook denies that idiom in the session that writes this
# file, which is the guard doing its job and not a reason to weaken it.
FROM ubuntu:24.04
RUN apt-get update \
 && apt-get install -y --no-install-recommends jq ca-certificates \
 && apt-get clean
ARG PROBE_UID
RUN test -n "$PROBE_UID" \
 && { existing="$(getent passwd "$PROBE_UID" | cut -d: -f1)"; [ -z "$existing" ] || userdel -r "$existing"; } \
 && useradd -m -u "$PROBE_UID" probe
USER probe
WORKDIR /home/probe
