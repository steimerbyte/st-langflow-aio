#!/bin/bash
# Verify MiniMax provider registration inside the running container.
# Usage: docker exec -it langflow /tmp/verify.sh
#
# Thin wrapper around verify_inplace.py. The real checks live in Python
# because the registry is in-memory and only a Python introspection can
# inspect it.

set -e
exec python3 /tmp/verify_inplace.py
