SHELL=/bin/bash
BUILDFLAGS=

.PHONY: latest upload-latest upload

latest:
	docker build \
		-t drawlti\:latest \
		-t gitlab-container.tba-hosting.de/lpa-aflek-alice/excalidraw-lti-application\:latest \
		--platform linux/x86-64 $(BUILDFLAGS) .

upload: upload-latest

upload-latest: latest
	docker push \
		gitlab-container.tba-hosting.de/lpa-aflek-alice/excalidraw-lti-application\:latest

messages:
	python manage.py makemessages --locale=de \
		--ignore="client" \
		--ignore="devscripts" \
		--ignore="ENV" \
		--ignore="htmlcov" \
		--ignore="tmp" \
		--add-location="file"

env:
	rm -rf ENV
	python3 -m venv ENV
	ENV/bin/python -m pip install -U pip wheel setuptools
	ENV/bin/python -m pip install -r requirements.txt
