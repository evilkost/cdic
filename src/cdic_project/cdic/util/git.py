# coding: utf-8

import os
import shutil
import logging

from typing import List, Iterable

import git
from git import Repo

log = logging.getLogger(__name__)


class GitException(Exception):
    pass


class AnotherRepoExists(GitException):
    pass


class RepoDoesNotExist(GitException):
    pass


class NothingToCommit(GitException):
    pass


class RemoteUndefined(GitException):
    pass


class GitStore(object):
    """

    File structure:
        <self.base_path>/<user name>/<project_name>/.git/
    """
    def __init__(self, base_path, ssh_bin=None):
        self.base_path = base_path
        # self.base_path = config["CDIC_WORKPLACE"]
        # self.ssh_bin = config.get("GITHUB_SSH_BIN", "/usr/bin/ssh")
        # git.Git.update_environment(GIT_SSH=self.ssh_bin)

        self.r = None

    def repo_path(self, username: str, projectname: str) -> str:
        return os.path.join(self.base_path, username.lower(), projectname.lower())

    def clean(self, username, projectname):
        repo = self.repo_path(username, projectname)
        log.info("Going to delete: {}".format(repo))
        shutil.rmtree(repo, ignore_errors=True)

    def init_local(self, username, projectname) -> Repo:
        repo = self.repo_path(username, projectname)
        self.check_git_not_exists(repo)
        self.create_dir(repo)

        return git.Repo.init(repo)

    def get_existing_repo(self, username, projectname) -> Repo:
        repo = self.repo_path(username, projectname)
        self.check_git_exists(repo)
        return Repo(repo)

    def remove_local(self, username, projectname):
        shutil.rmtree(self.repo_path(username, projectname))

    # def add_remote_by_name(self, username, projectname, remote_git_url, remote_name):
    #     repo = self.get_existing_repo(username, projectname)
    #     self.add_remote(repo, remote_git_url, remote_name)

    @staticmethod
    def _get_remote(repo, remote_name):
        try:
            return repo.remotes[remote_name]
        except IndexError:
            return None

    @classmethod
    def add_remote(cls, repo: Repo,
                   remote_git_url: str, remote_name: str=None):
        remote_name = remote_name or "origin"
        if cls._get_remote(repo, remote_name):
            log.warn("Repeatedly adding remote: {}".format(remote_name))
            return

        return repo.create_remote(remote_name, remote_git_url)

    @classmethod
    def push_remote(cls, repo: Repo, remote_name: str=None,
                    local_branch: str=None, remote_branch: str=None) -> "List[PushInfo]":
        """
        :param remote_name: default `origin`
        :param local_branch: not implemented yet
        :param remote_branch: default `master`
        """
        remote_name = remote_name or "origin"
        rem = cls._get_remote(repo, remote_name)
        if rem is None:
            raise RemoteUndefined("Repo `{}` doesn't have a remote: {}"
                                  .format(repo, remote_name))

        local_branch = local_branch or "master"
        remote_branch = remote_branch or "master"
        refspec = "{}:{}".format(local_branch, remote_branch)

        return rem.push(refspec, force=True)

    @staticmethod
    def initial_commit(repo: Repo, to_commit: Iterable[str],  message: str=None):
        repo.index.add(to_commit)
        msg = message or "Initial commit of {}".format(", ".join(to_commit))
        repo.index.commit(msg)

    @staticmethod
    def commit_changes(repo: Repo, to_commit: Iterable[str],  message: str=None):
        # TODO: doesn't exists before the first commit, handle exception here
        # import ipdb; ipdb.set_trace()
        # if repo.head.commit.diff():
        if repo.is_dirty():
            repo.index.add(to_commit)
            msg = message or "Autocommit of {}".format(", ".join(to_commit))
            repo.index.commit(msg)
        else:
            log.debug("Nothing to commit Repo: {}, to_commit: {}, message: {}"
                      .format(repo, to_commit, message))
        # else:
        #     raise NothingToCommit("Repo: {}, to_commit: {}, message: {}"
        #                           .format(repo, to_commit, message))

    @staticmethod
    def check_git_not_exists(repo_path):
        git_path = os.path.join(repo_path, ".git")
        if os.path.isdir(git_path):
            raise AnotherRepoExists("Path: `{}` already contains a git repo"
                                    .format(repo_path))

    @staticmethod
    def check_git_exists(repo_path):
        git_path = os.path.join(repo_path, ".git")
        if not os.path.isdir(git_path):
            raise RepoDoesNotExist("Repo doesn't exist a: `{}`"
                                   .format(repo_path))

    @staticmethod
    def create_dir(repo_path):
        if not os.path.exists(repo_path):
            os.makedirs(repo_path)


