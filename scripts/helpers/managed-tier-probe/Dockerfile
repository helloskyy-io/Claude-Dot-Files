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
# `apt-get clean` rather than the usual `rm -rf /var/lib/apt/lists/*`: the
# fleet's own safety hook denies that idiom in the session that writes this
# file, which is the guard doing its job and not a reason to weaken it.
FROM ubuntu:24.04
RUN apt-get update \
 && apt-get install -y --no-install-recommends jq ca-certificates \
 && apt-get clean
RUN useradd -m -u 1001 probe
USER probe
WORKDIR /home/probe
