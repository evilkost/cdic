# coding: utf-8

from distutils.core import setup

setup(
    name="cdic",
    package_dir={'cdic': 'src/cdic'},
    packages=["cdic"],
    version="0.0",
    description="Service to inject copr repo into the Docker files",
    author="Valentin Gologuzov",
    author_email="vgologuz@redhat.com",
    url="http://github.com/evilkost/cdic",
    keywords=["copr", "docker", "repo"],
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Framework :: Flask",
        "Development Status :: 1 - Planning",
        "Environment :: Other Environment",
        "Operating System :: POSIX :: Linux :: Fedora",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    ]
)
