#!/usr/bin/env bash
# Trusted, static guest launcher. No PDF/password is ever placed in argv/env/file.
set -euo pipefail
case "${1:-}" in
  probe) script=/srv/backend/app/p5h_vm_guest_probe.py ;;
  parse) script=/srv/backend/app/p5h_vm_guest_child.py ;;
  *) exit 66 ;;
esac
exec /usr/bin/bwrap \
  --die-with-parent --unshare-all --new-session --cap-drop ALL --clearenv \
  --setenv PYTHONDONTWRITEBYTECODE 1 --setenv PYTHONIOENCODING utf-8 \
  --tmpfs / \
  --dir /usr --ro-bind /usr /usr \
  --dir /lib --ro-bind-try /lib /lib \
  --dir /lib64 --ro-bind-try /lib64 /lib64 \
  --dir /srv --dir /srv/backend --dir /srv/backend/app \
  --ro-bind /srv/backend/app /srv/backend/app \
  --dir /tmp --tmpfs /tmp --dir /proc --proc /proc \
  --dir /dev --dev /dev --chdir /tmp \
  -- /usr/local/p5h-venv/bin/python -I -B "$script"
