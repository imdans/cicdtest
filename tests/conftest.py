"""Re-export unit fixtures for all tests.

Supports both running pytest from repo root and from within tests/.
"""

try:
	# Prefer package-relative import when tests is a package
	from .unit.conftest import *  # type: ignore  # noqa: F401,F403
except Exception:  # pragma: no cover - fallback for non-package execution
	import importlib.util
	import pathlib
	import sys

	unit_path = pathlib.Path(__file__).parent / 'unit' / 'conftest.py'
	spec = importlib.util.spec_from_file_location('unit_conftest', unit_path)
	if spec and spec.loader:
		module = importlib.util.module_from_spec(spec)
		sys.modules['unit_conftest'] = module
		spec.loader.exec_module(module)
		# import all public names
		for k, v in module.__dict__.items():
			if not k.startswith('_'):
				globals()[k] = v
