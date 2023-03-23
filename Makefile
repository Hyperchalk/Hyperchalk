SHELL := bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c
.DELETE_ON_ERROR:
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules

ROOT_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

# retrieve the software version from the draw/__init__.py file
HC_VERSION := $(shell grep -hE "^__version__ =" draw/__init__.py | grep -ohE '(\d\.?)+')

# TODO: compile messages in the Dockerfile
latest:
	python manage.py compilemessages
	docker build \
		-t hyperchalk\:latest -t hyperchalk\:$(HC_VERSION) \
		-t ghcr.io/hyperchalk/hyperchalk\:latest -t ghcr.io/hyperchalk/hyperchalk\:$(HC_VERSION) \
		--platform linux/x86-64 $(BUILDFLAGS) .
.PHONY: latest


upload-latest: latest
	docker push \
		ghcr.io/hyperchalk/hyperchalk\:latest
	docker push \
		ghcr.io/hyperchalk/hyperchalk\:$(HC_VERSION)
upload: upload-latest
.PHONY: upload-latest upload


messages:
	python manage.py makemessages --locale=de \
		--ignore="client" \
		--ignore="devscripts" \
		--ignore="ENV" \
		--ignore="htmlcov" \
		--ignore="tmp" \
		--add-location="file"
.PHONY: messages


env:
	python3 -m venv env
	ENV/bin/python -m pip install -U pip wheel setuptools
	ENV/bin/python -m pip install -r requirements.txt


client/dist/app.js: $(shell find client/src -type f)
	docker run --rm \
		-v $(ROOT_DIR)/client/src:/srv/src \
		-v $(ROOT_DIR)/client/dist:/srv/dist \
		hyperchalk-client-builder\:latest
client: client/dist/app.js
.PHONY: client


client-watch:
	exec docker run --rm -it \
		-v $(ROOT_DIR)/client/src:/srv/src \
		-v $(ROOT_DIR)/client/dist:/srv/dist \
		hyperchalk-client-builder\:latest watch
.PHONY: client-watch


client-builder.log: $(shell find client -type f -and -not -path 'client/src/*' -and -not -path 'client/dist/*')
	cd app/client
	docker build -t hyperchalk-client-builder\:latest . \
	| tee client-builder.log
client-builder: client-builder.log
.PHONY: client-builder


admin:
	docker run --rm -it --entrypoint gosu \
		-v $(ROOT_DIR):/srv \
		ghcr.io/hyperchalk/hyperchalk\:latest \
		ltiapp devscripts/create_admin.sh
.PHONY: admin
