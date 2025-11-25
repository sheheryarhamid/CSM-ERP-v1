"""Legacy mock secure files module (deprecated).

The real implementation lives in `hub/secure_files_impl.py`. This placeholder
raises at import time to prevent accidental use of the demo mock in feature
branches. Import `secure_files_impl` instead.
"""

raise RuntimeError("hub.secure_files is deprecated. Import hub.secure_files_impl instead.")
