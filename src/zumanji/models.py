import base64
from django.db import models
from django.utils import simplejson


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


class Revision(models.Model):
    project = models.ForeignKey(Project)
    label = models.CharField(max_length=64)
    data = GzippedJSONField(default={}, blank=True)

    class Meta:
        unique_together = (('project', 'label'),)

    def __unicode__(self):
        return self.label


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

    def _get_temporal_sibling(self, datetime_filter, order_field, tag=None):
        filter_args = {
            'project': self.project,
            datetime_filter: self.datetime
        }
        if tag:
            filter_args["tags"] = tag

        try:
            return type(self).objects.filter(
                **filter_args
            ).exclude(
                id=self.id,
            ).order_by(order_field)[0]
        except IndexError:
            return None

    def get_previous_build(self, tag=None):
        return self._get_temporal_sibling('datetime__lt', "-datetime", tag)

    def get_next_build(self, tag=None):
        return self._get_temporal_sibling('datetime__gt', "datetime", tag)


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
                build__datetime__lt=self.build.datetime,
                label=self.label,
            ).exclude(
                build=self.build,
            ).order_by('-build__datetime')[0]
        except IndexError:
            return None

    def get_test_in_next_build(self):
        try:
            return type(self).objects.filter(
                build__project=self.project,
                build__datetime__gt=self.build.datetime,
                label=self.label,
            ).exclude(
                build=self.build,
            ).order_by('build__datetime')[0]
        except IndexError:
            return None

    def get_previous_builds(self):
        return Build.objects.filter(
            project=self.project,
            datetime__lt=self.build.datetime,
            test__label=self.label,
        ).exclude(
            id=self.build.id,
        ).order_by('-datetime')

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
