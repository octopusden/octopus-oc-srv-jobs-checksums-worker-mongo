FROM python:3.7

USER root

RUN rm -rf /build
COPY --chown=root:root . /build
WORKDIR /build
RUN python3 -m pip install $(pwd) && \
    python3 -m unittest discover -v && \
    python3 setup.py bdist_wheel

ENTRYPOINT ["python3", "-m", "oc_checksumsworker_mongo"]
