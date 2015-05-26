# FROM fedora:21
#FROM fedora/systemd-systemd:latest
FROM vpavlin/fedora:systemd


RUN yum install -y dnf && \
    dnf install -y \
        python3 \
        python3-pip \
        python3-gunicorn \
        git \
        redis \
        vim \
        wget \
        dnf-plugins-core \
        python3-psycopg2

RUN dnf copr enable msuchy/copr -y && \
    dnf install -y phantomjs && \
    mkdir -p /opt/casper && cd /opt/casper && git clone git://github.com/n1k0/casperjs.git && \
    cd casperjs && ln -sf `pwd`/bin/casperjs /usr/bin/casperjs && chmod +x /usr/bin/casperjs

RUN mkdir -p /opt/cdic && cd /opt/ && git clone https://github.com/evilkost/cdic.git && \
    cd /opt/cdic && pip3 install -r requirements.txt

#RUN mkdir -p /opt/cdic/src
#COPY requirements.txt /opt/cdic/
#COPY src /opt/cdic/src
#RUN cd /opt/cdic && pip3 install -r requirements.txt

COPY _docker/private /opt/cdic/_docker/private
COPY _docker/systemd /opt/cdic/_docker/systemd
EXPOSE 8000


RUN adduser cdic && chown -Rf cdic:cdic /opt/cdic

RUN cp /opt/cdic/_docker/systemd/* /etc/systemd/system/ \
    && cp /opt/cdic/_docker/tmpfiles.d/* /etc/tmpfiles.d/ \
    && mkdir -p /home/cdic/.config \
    && mkdir -p /home/cdic/private/.ssh \
    && mkdir -p /var/log/cdic \
    &&  chown -R cdic:cdic  /var/log/cdic \
    && chmod +x /opt/cdic/_docker/first_run.sh \
    && mkdir -p /var/lib/cdic && chown -R cdic:cdic  /var/lib/cdic \
    && mkdir -p /home/cdic/.ssh/ \
    && cp /opt/cdic/_docker/private/id_rsa /home/cdic/.ssh/ \
    && cp /opt/cdic/_docker/ssh_config /home/cdic/.ssh/config \
    && chmod -R 600  /home/cdic/.ssh/* \
    && chown -R cdic:cdic /home/cdic/ \
    && systemctl enable redis cdic_async cdic_gunicorn
    # && cp /opt/cdic/_docker/private/cdic.py /home/cdic/.config/ \

VOLUME  ["/etc/cdic", "/var/lib/cdic"]

COPY _docker/entry_point.sh /opt/entry_point.sh

ENTRYPOINT ["/opt/entry_point.sh"]
CMD ["/usr/sbin/init"]
# TODO: private date shouldn't be embeded into the image, we should provide them from the host system at start
