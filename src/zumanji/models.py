import base64
import dateutil.parser
from django.db import models
from django.db.models import Q
from django.utils import simplejson
from zumanji.github import github


RESULT_CHOICES = tuple((k, k) for k in (
    'success',
    'failed',
    'skipped',
    'deprecated',
))


class GzippedJSONField(models.TextField):
    """
    Slightly different from a JSONField in the sense that the default
    value is a dictionary.
    """
    __metaclass__ = models.SubfieldBase

    def to_python(self, value):
        if isinstance(value, basestring) and value:
            try:
                value = simplejson.loads(base64.b64decode(value).decode('zlib'))
            except Exception:
                return {}
        elif not value:
            return {}
        return value

    def get_prep_value(self, value):
        if value is None:
            return
        return base64.b64encode(simplejson.dumps(value).encode('zlib'))

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_prep_value(value)

    def south_field_triple(self):
        "Returns a suitable description of this field for South."
        from south.modelsinspector import introspector
        field_class = "django.db.models.fields.TextField"
        args, kwargs = introspector(self)
        return (field_class, args, kwargs)


class Project(models.Model):
    label = models.CharField(max_length=64, unique=True)
    data = GzippedJSONField(default={}, blank=True)

    def __unicode__(self):
        return self.label

    def save(self, *args, **kwargs):
        assert '/' in self.label, 'Label must in format of user/repo (GitHub-esque)'

        return super(Project, self).save(*args, **kwargs)

    @property
    def github_user(self):
        return self.label.split('/', 1)[0]

    @property
    def github_repo(self):
        return self.label.split('/', 1)[1]


class Revision(models.Model):
    project = models.ForeignKey(Project)
    label = models.CharField(max_length=64)
    datetime = models.DateTimeField(null=True)
    parent = models.ForeignKey('self', null=True)
    data = GzippedJSONField(default={}, blank=True)

    class Meta:
        unique_together = (('project', 'label'),)

    def __unicode__(self):
        return self.label

    @classmethod
    def sanitize_github_data(cls, data):
        return {
            'commit': data['commit'],
            'stats': data['stats'],
            'files': [{'filename': f['filename']} for f in data['files']],
        }

    @classmethod
    def get_or_create(cls, project, label):
        """
        Get a revision, and if it doesnt exist, attempt to pull it from Git.
        """
        try:
            rev = cls.objects.get(project=project, label=label)
        except Revision.DoesNotExist:
            data = github.get_commit(project.github_user, project.github_repo, label)

            datetime = dateutil.parser.parse(data['commit']['committer']['date'])
            # LOL MULTIPLE PARENTS HOW DOES GIT WORK
            # (dont care about the merge commits parent for our system)
            if data.get('parents'):
                parent = cls.get_or_create(project, data['parents'][0]['sha'])
            else:
                parent = None

            return cls.objects.create(
                project=project,
                label=label,
                datetime=datetime,
                parent=parent,
                data=cls.sanitize_github_data(data),
            )

        return rev

    @property
    def details_url(self):
        return github.get_commit_url(self.project.github_user, self.project.github_repo, self.label)

    @property
    def oneline(self):
        return self.data['commit']['message'].split('\n', 1)[0]

    @property
    def summary(self):
        return '\n'.join(self.data['commit']['message'].split('\n', 1)[1:])

    @property
    def author(self):
        return self.data['commit']['author']


class Build(models.Model):
    project = models.ForeignKey(Project)
    revision = models.ForeignKey(Revision)
    datetime = models.DateTimeField()
    num_tests = models.PositiveIntegerField(default=0)
    total_duration = models.FloatField(default=0.0)
    data = GzippedJSONField(default={}, blank=True)
    result = models.CharField(max_length=16, choices=RESULT_CHOICES, null=True)

    class Meta:
        unique_together = (('revision', 'datetime'),)

    def __unicode__(self):
        return unicode(self.datetime)

    def save(self, *args, **kwargs):
        self.project = self.revision.project
        super(Build, self).save(*args, **kwargs)

    def _get_temporal_sibling(self, datetime_filter, order_field, tag=None, previous=False):
        filter_args = {
            'project': self.project,
            # datetime_filter: self.revision.datetime
        }
        if tag:
            filter_args["tags"] = tag

        qs = type(self).objects.filter(**filter_args)

        if previous:
            qs = qs.filter(Q(revision=self.revision.parent) | Q(revision__isnull=True))
        else:
            qs = qs.filter(revision__parent=self.revision)

        try:
            return qs.exclude(
                id=self.id,
            ).select_related('revision').order_by(order_field)[0]
        except IndexError:
            return None

    def get_previous_build(self, tag=None):
        return self._get_temporal_sibling('revision__datetime__lt', "-revision__datetime", tag, previous=True)

    def get_next_build(self, tag=None):
        return self._get_temporal_sibling('revision__datetime__gt', "revision__datetime", tag)


class BuildTag(models.Model):
    builds = models.ManyToManyField(Build, related_name='tags')
    label = models.CharField(max_length=255)

    def __unicode__(self):
        return self.label


class Test(models.Model):
    project = models.ForeignKey(Project)
    revision = models.ForeignKey(Revision)
    build = models.ForeignKey(Build)
    parent = models.ForeignKey('self', null=True)
    label = models.CharField(max_length=255)
    description = models.TextField(null=True)
    num_tests = models.PositiveIntegerField(default=0)
    mean_duration = models.FloatField(default=0.0)
    upper_duration = models.FloatField(default=0.0)
    lower_duration = models.FloatField(default=0.0)
    upper90_duration = models.FloatField(default=0.0)
    data = GzippedJSONField(default={}, blank=True)
    result = models.CharField(max_length=16, choices=RESULT_CHOICES, null=True)

    class Meta:
        unique_together = (('build', 'label'),)

    def __unicode__(self):
        return self.label

    def save(self, *args, **kwargs):
        if self.parent:
            self.build = self.parent.build
        self.revision = self.build.revision
        self.project = self.revision.project
        super(Test, self).save(*args, **kwargs)

    def shortlabel(self):
        if not self.parent:
            return self.label
        return self.label[len(self.parent.label) + 1:]

    def get_test_in_previous_build(self):
        try:
            return type(self).objects.filter(
                build__project=self.project,
                build__revision__datetime__lt=self.revision.datetime,
                build__revision=self.revision.parent,
                label=self.label,
            ).exclude(
                build=self.build,
            ).order_by('-build__revision__datetime')[0]
        except IndexError:
            return None

    def get_test_in_next_build(self):
        try:
            return type(self).objects.filter(
                build__project=self.project,
                build__revision__datetime__gt=self.revision.datetime,
                build__revision__parent=self.revision,
                label=self.label,
            ).exclude(
                build=self.build,
            ).order_by('build__revision__datetime')[0]
        except IndexError:
            return None

    def get_previous_builds(self, limit=50):
        build = self.build
        builds = []
        for x in xrange(limit):
            previous_build = build.get_previous_build()
            if previous_build is None:
                break
            builds.append(previous_build)
            build = previous_build
        return builds

    def get_context(self):
        # O(N), so dont abuse it
        nodes = []
        parent = self
        while parent:
            nodes.append(parent)
            parent = parent.parent
        nodes.reverse()
        return nodes


class TestData(models.Model):
    project = models.ForeignKey(Project)
    revision = models.ForeignKey(Revision)
    build = models.ForeignKey(Build)
    test = models.ForeignKey(Test)
    key = models.CharField(max_length=32)
    data = GzippedJSONField(default={}, blank=True)

    class Meta:
        unique_together = (('test', 'key'),)

    def save(self, *args, **kwargs):
        self.build = self.test.build
        self.revision = self.build.revision
        self.project = self.revision.project
        super(TestData, self).save(*args, **kwargs)
