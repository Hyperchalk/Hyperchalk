# Excalidraw for LTI

This is a port of the [Excalidraw](https://excalidraw.com) app to support LTI and data collection,
enabling its usage for learning analytics in LMS courses.

## Installation and Configuration

It is recommended to use the docker container for deploying this application. The container is
available via `gitlab-container.tba-hosting.de/lpa-aflek-alice/excalidraw-lti-application:latest`.

An example configuration of the docker app is contained in `docker-compose.example.yml`. Download
this file as well as the `local_settings.example.py`, rename both and change the configurations
according to your needs. The `local_settings.example.py` contains configuration documentation and
some TODOs. You can use these to get an orientation.

It is recommended that you either supply you own database or that you configure one via the docker
compose file. The example configuration shows how to configure the app using sqlite. This is not
recommended though if you use more than one worker / process. The same goes for the channel layers
backend. Have a look at the example configuration for further explanation.

The container uses [gunicorn](https://gunicorn.org/) to deliver the app. You might want to check
out the configuration options for that when configuring the container. As the gunicorn worker
class, [unicorn](https://www.uvicorn.org/) is used to support async views. This is also needed to
enable websocket support, which is crucial for the app.

It is assumend that you configure static file serving in your web server, which also serves as a
reverse proxy for the application. As an example, this repo includes an example configuration for
nginx in the `nginx-site.example.conf` file.
