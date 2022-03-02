SHELL=/bin/bash
BUILDFLAGS=

.PHONY: base redischannel upload-latest upload-redischannel upload

upload: upload-latest upload-redischannel

base:
	docker build \
		-t drawlti\:latest \
		-t gitlab-container.tba-hosting.de/lpa-aflek-alice/excalidraw-lti-application\:latest \
		--platform linux/x86-64 $(BUILDFLAGS) .

redischannel: base
	docker build \
		-f redischannel.Dockerfile \
		-t drawlti\:redischannel \
		-t gitlab-container.tba-hosting.de/lpa-aflek-alice/excalidraw-lti-application\:redischannel \
		--platform linux/x86-64 $(BUILDFLAGS) .

upload-latest: base
	docker push \
		gitlab-container.tba-hosting.de/lpa-aflek-alice/excalidraw-lti-application\:latest

upload-redischannel: redischannel
	docker push \
		gitlab-container.tba-hosting.de/lpa-aflek-alice/excalidraw-lti-application\:redischannel

messages:
	python manage.py makemessages --locale=de \
		--ignore="client" \
		--ignore="devscripts" \
		--ignore="ENV" \
		--ignore="htmlcov" \
		--ignore="tmp" \
		--add-location="file"

translate-german:
	python manage.py compilemessages --locale=de
