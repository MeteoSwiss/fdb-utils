# This Dockerfile is used to build a test environment for the library that contains git, FDB5 and ECCODES libraries.

FROM dockerhub.apps.cp.meteoswiss.ch/numericalweatherpredictions/fdb-data-poller:1.13.0 AS dependencies

FROM dockerhub.apps.cp.meteoswiss.ch/mch/python-3.11

RUN mkdir -p /opt/spack-root/ /opt/spack-view/

COPY --from=dependencies /opt/spack-root /opt/spack-root/
COPY --from=dependencies /opt/spack-view /opt/spack-view/
COPY --from=dependencies /opt/eccodes-cosmo /opt/eccodes-cosmo/
COPY --from=dependencies /opt/eccodes-cosmo-mars /opt/eccodes-cosmo-mars/

ENV ECCODES_DEFINITION_PATH=/opt/eccodes-cosmo/definitions:/opt/eccodes-cosmo-mars/definitions:/opt/spack-view/share/eccodes/definitions
ENV ECCODES_DIR=/opt/spack-view/
ENV FDB5_DIR=/opt/spack-view/
ENV PATH="/opt/spack-view/bin:${PATH}"

RUN apt-get -yqq update \
    && apt-get -yqq install --no-install-recommends \
    git
