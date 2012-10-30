from django.conf import settings
import requests


class RequestError(Exception):
    pass


class GitHub(object):
    def __init__(self, access_token, host='https://api.github.com'):
        self.access_token = access_token
        self.host = host

    def request(self, method, path, params={}):
        response = getattr(requests, method.lower())('%s/%s?access_token=%s' % (self.host, path, self.access_token),
            **params)
        if response.status_code != 200:
            raise RequestError(response.json['message'])
        return response.json

    def get_commit(self, repo, sha):
        return self.request('GET', 'repos/%s/commits/%s' % (repo, sha))

    def get_commit_url(self, repo, sha):
        return '%s/%s/commit/%s' % (self.host.replace('api.', ''), repo, sha)


github = GitHub(access_token=settings.GITHUB_ACCESS_TOKEN)
