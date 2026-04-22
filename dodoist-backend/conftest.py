import os

# Ensure DEBUG=true during test runs so the fail-fast SECRET_KEY check is bypassed.
os.environ.setdefault("DJANGO_DEBUG", "true")
