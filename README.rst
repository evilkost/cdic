Cdic
====

- Copr
- Docker
- Image
- Composer

Small service to patch Dockerfiles.
Injects code into the Dockerfile to enable Copr repos.

Before deploy
-------------

- Create github & dockerhub accounts
- Setup ssh key pair for github, don't use passphrase
- Create api token at github with permissions: ``admin:org_hook, admin:public_key, admin:repo_hook, delete_repo, notifications, read:org, repo, use``
- Login into dockerhub and go to https://registry.hub.docker.com/builds/link/github/ and select connection type
