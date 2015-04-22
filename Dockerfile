FROM fedora:21

RUN yum install -y dnf && \
    dnf install -y python3 python3-pip python3-gunicorn git

RUN mkdir -p /opt/cdic && cd /opt/ && git clone https://github.com/evilkost/cdic.git && \
    cd cdic && pip3 install -r requirements.txt

COPY _docker /opt/cdic/_docker
EXPOSE 8080

CMD ["/opt/cdic/_docker/entry_point.sh"]


