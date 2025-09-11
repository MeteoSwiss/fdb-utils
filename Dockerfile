# This Dockerfile is used to build a test environment for the library that contains git, FDB5 and ECCODES libraries.

FROM dockerhub.apps.cp.meteoswiss.ch/numericalweatherpredictions/fdb-data-poller-base:latest AS dependencies

FROM dockerhub.apps.cp.meteoswiss.ch/mch/python-3.11

RUN mkdir -p /opt/spack-root/ /opt/spack-view/

COPY --from=dependencies /opt/spack-root /opt/spack-root/
COPY --from=dependencies /opt/spack-view /opt/spack-view/

ENV ECCODES_DIR=/opt/spack-view/
ENV FDB5_HOME=/opt/spack-view/
ENV PATH="/opt/spack-view/bin:${PATH}"

RUN apt-get -yqq update \
    && apt-get -yqq install --no-install-recommends \
    git
