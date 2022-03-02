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
class, [uvicorn](https://www.uvicorn.org/) is used to support async views. This is also needed to
enable websocket support, which is crucial for the app.

It is assumend that you configure static file serving in your web server, which also serves as a
reverse proxy for the application. As an example, this repo includes an example configuration for
nginx in the `nginx-site.example.conf` file.

When the container is started, the database is automatically being migrated and new static files are
collected.

## Useful Configuration Documentation Links

You are not restricted to just configuring the things in the example files. For further options,
check out the following sources:

- [Django Deployment Guide] (especially the section where [Gunicorn deployment] is explained.)
- [Django Settings Guide] and [settings reference]
- [Channel Layers Configuration](https://channels.readthedocs.io/en/stable/topics/channel_layers.html#configuration)
- [Gunicorn Configuration](https://docs.gunicorn.org/en/latest/configure.html)
- [Uvicorn Settings Documentation](https://www.uvicorn.org/settings/)
- [Uvicorn Deployment Guide](https://www.uvicorn.org/deployment/)

[Django Deployment Guide]: https://docs.djangoproject.com/en/3.2/howto/deployment/
[Gunicorn deployment]: https://docs.djangoproject.com/en/3.2/howto/deployment/wsgi/gunicorn/
[Django Settings Guide]: https://docs.djangoproject.com/en/3.2/topics/settings/
[settings reference]: https://docs.djangoproject.com/en/3.2/ref/settings/

## Useful Commands

You can run any django management command via `docker-compose run --rm drawapp manage COMMAND`. Some
useful ones for this projects are:

```sh
# create an admin user for logging in to the admin backened
$ docker-compose run --rm drawapp manage createsuperuser

# create a registration link
$ docker-compose run --rm drawapp manage makeconsumerlink
```