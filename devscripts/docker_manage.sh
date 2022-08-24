BASEDIR=$(cd "$(dirname "$0")"; pwd)
source "$BASEDIR/init.sh"
cd "$BASEDIR/.."

docker run --rm -it --entrypoint gosu \
    -v $PWD:/srv \
    gitlab-container.tba-hosting.de/lpa-aflek-alice/excalidraw-lti-application\:latest \
    ltiapp python manage.py $@
