import mock
from django.core.urlresolvers import reverse
from django.test import TestCase, Client
from django.test.utils import override_settings
from zumanji.models import Project


class UploadCSRFTest(TestCase):
    def setUp(self):
        self.project = Project.objects.create(label='test')
        self.path = reverse('zumanji:upload_project_build', kwargs={
            'project_label': self.project.label,
        })
        self.client = Client(enforce_csrf_checks=True)

    def get_mock_file(self):
        result = mock.Mock()
        result.name = 'foo.json'
        result.read.return_value = '{}'
        return result

    @mock.patch('zumanji.views.import_build')
    def test_csrf_expected_without_api_key(self, import_build):
        import_build.return_value.id = 1
        resp = self.client.post(self.path, {
            'json_file': self.get_mock_file(),
        })
        self.assertEquals(resp.status_code, 403)
        self.assertFalse(import_build.called)

    @override_settings(ZUMANJI_CONFIG={'API_KEY': 'foo'})
    @mock.patch('zumanji.views.import_build')
    def test_csrf_not_used_with_api_key(self, import_build):
        import_build.return_value.id = 1
        resp = self.client.post(self.path, {
            'json_file': self.get_mock_file(),
            'api_key': 'foo',
        })
        self.assertEquals(resp.status_code, 302)
        self.assertTrue(import_build.called)
