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

    def request(self, method, url, params=None):
        request = self.build_request(method, url, params)
        return self.get_response(request).json

    def build_request(self, method, url, params=None):
        if params and method.upper() == 'GET':
            kwargs = {'params': params.copy()}
        else:
            kwargs = {'data': params, 'params': {}}

        kwargs['params']['access_token'] = self.access_token

        if '://' not in url:
            url = '%s/%s' % (self.host, url)

        return (method, url, kwargs)

    def get_response(self, request):
        method, url, kwargs = request
        logging.info('Fetching %s', url)
        response = getattr(requests, method.lower())(url, **kwargs)
        if response.status_code == 404:
            raise NotFound(response.json['message'])
        elif response.status_code != 200:
            raise RequestError(response.json['message'])
        return response

    def get_commit(self, user, repo, sha):
        return self.request('GET', 'repos/%s/%s/commits/%s' % (user, repo, sha))

    def get_commit_url(self, user, repo, sha):
        return '%s/%s/%s/commit/%s' % (self.host.replace('api.', ''), user, repo, sha)

    def iter_commits(self, user, repo):
        stack = []

        request = self.build_request('GET', 'repos/%s/%s/commits' % (user, repo), {
            'per_page': 100,
        })
        while True:
            response = self.get_response(request)
            data = response.json
            if not data:
                break

            for result in data:
                stack.append(result)

            if 'next' not in response.links:
                break

            pagelink = response.links['next']['url']
            request = self.build_request('GET', pagelink)

        # FML
        for result in reversed(stack):
            yield result

    def compare_commits(self, user, repo, prev, cur='HEAD'):
        return self.request('GET', 'repos/%s/%s/compare/%s...%s' % (user, repo, prev, cur))

github = GitHub(access_token=settings.GITHUB_ACCESS_TOKEN)
