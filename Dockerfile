# FROM fedora:21
#FROM fedora/systemd-systemd:latest
FROM vpavlin/fedora:systemd


RUN yum install -y dnf && \
    dnf install -y python3 python3-pip python3-gunicorn git

RUN mkdir -p /opt/cdic && cd /opt/ && git clone https://github.com/evilkost/cdic.git && \
    cd cdic && pip3 install -r requirements.txt

COPY _docker /opt/cdic/_docker
EXPOSE 8000

RUN adduser cdic && chown -Rf cdic:cdic /opt/cdic

RUN cp /opt/cdic/_docker/systemd/* /etc/systemd/system/ && \
    cp /opt/cdic/_docker/tmpfiles.d/* /etc/tmpfiles.d/ && \
    mkdir -p /home/cdic/.config && \
    cp /opt/cdic/_docker/cdic.py /home/cdic/.config/ && \
    chown -R cdic:cdic /home/cdic/ && \
    systemctl enable cdic_gunicorn


# CMD ["/opt/cdic/_docker/entry_point.sh"]

CMD ["/usr/sbin/init"]


