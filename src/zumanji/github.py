from django.conf import settings
import logging
import requests


github_logger = logging.getLogger('github.api')


class RequestError(Exception):
    pass


class NotFound(Exception):
    pass


class GitHub(object):
    def __init__(self, access_token, host='https://api.github.com'):
        self.access_token = access_token
        self.host = host

    def request(self, method, path, params={}):
        logging.info('Fetching %s', path)
        response = getattr(requests, method.lower())('%s/%s?access_token=%s' % (self.host, path, self.access_token),
            **params)
        if response.status_code == 404:
            raise NotFound(response.json['message'])
        elif response.status_code != 200:
            raise RequestError(response.json['message'])
        return response.json

    def get_commit(self, user, repo, sha):
        return self.request('GET', 'repos/%s/%s/commits/%s' % (user, repo, sha))

    def get_commit_url(self, user, repo, sha):
        return '%s/%s/%s/commit/%s' % (self.host.replace('api.', ''), user, repo, sha)

    def compare_commits(self, user, repo, prev, cur='HEAD'):
        return self.request('GET', 'repos/%s/%s/compare/%s...%s' % (user, repo, prev, cur))

github = GitHub(access_token=settings.GITHUB_ACCESS_TOKEN)
