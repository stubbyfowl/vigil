PY := .venv/bin/python
OFFSCREEN := QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software

.PHONY: setup native dev demo kiosk data eval test lint screenshots package

setup:
	test -d .venv || python3 -m venv .venv
	.venv/bin/pip install -q -r backend/requirements-dev.txt
	-$(MAKE) native

# Optional C++ tracker. If a compiler is missing, Vigil uses the Python tracker with identical results.
native:
	c++ -std=c++17 -O2 -ffp-contract=off -shared -fPIC backend/native/vigil_fast.cpp -o backend/app/engine/_vigil_fast.so

# Open the app in a window.
dev:
	$(PY) frontend/main.py --ground

# Open the app and play the Demo Director.
demo:
	$(PY) scripts/demo_director.py

# Fullscreen, for a dedicated panel. With no desktop running, add: --platform eglfs
kiosk:
	$(PY) frontend/main.py --kiosk

data:
	$(PY) scripts/generate_data.py

eval:
	$(PY) scripts/evaluate_detector.py

test:
	cd backend && $(OFFSCREEN) ../$(PY) -m pytest -q

lint:
	.venv/bin/ruff check backend frontend scripts
	cd backend && ../.venv/bin/mypy app

screenshots:
	$(PY) scripts/screenshots.py

# Build a standalone folder in dist/vigil. Run this on the operating system you are targeting.
package:
	.venv/bin/pyinstaller --noconfirm packaging/vigil.spec
