# This Dockerfile is used to build a test environment for the library

FROM dockerhub.apps.cp.meteoswiss.ch/numericalweatherpredictions/fdb-data-poller-base:latest AS dependencies

FROM dockerhub.apps.cp.meteoswiss.ch/mch/python-3.11

RUN mkdir -p /root/spack-root/

COPY --from=dependencies /root/spack-root/ /root/spack-root/

ENV ECCODES_DIR=/root/spack-root/eccodes/
ENV FDB5_HOME=/root/spack-root/fdb/