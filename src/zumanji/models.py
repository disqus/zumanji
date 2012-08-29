from django.db import models
from jsonfield import JSONField


class TestMixin(object):
    def is_alert(self):
        return self.duration >= 1

    def is_warning(self):
        return self.duration >= 0.5

    def is_starred(self):
        return self.duration < 0.1


class Project(models.Model):
    label = models.CharField(max_length=64)
    data = JSONField(default={})

    def __unicode__(self):
        return self.label


class Revision(models.Model):
    project = models.ForeignKey(Project)
    label = models.CharField(max_length=64)
    data = JSONField()

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
    data = JSONField(default={})

    class Meta:
        unique_together = (('revision', 'datetime'),)

    def __unicode__(self):
        return unicode(self.datetime)

    def save(self, *args, **kwargs):
        self.project = self.revision.project
        super(Build, self).save(*args, **kwargs)

    def get_previous_build(self):
        try:
            return type(self).objects.filter(
                datetime__lt=self.datetime
            ).exclude(
                id=self.id,
            ).order_by('-datetime')[0]
        except IndexError:
            return None

    def get_next_build(self):
        try:
            return type(self).objects.filter(
                datetime__gt=self.datetime
            ).exclude(
                id=self.id,
            ).order_by('datetime')[0]
        except IndexError:
            return None


class Test(models.Model, TestMixin):
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
    data = JSONField(default={})

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

    def get_test_in_previous_build(self):
        try:
            return type(self).objects.filter(
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
                build__datetime__gt=self.build.datetime,
                label=self.label,
            ).exclude(
                build=self.build,
            ).order_by('build__datetime')[0]
        except IndexError:
            return None

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
    key = models.CharField(max_length=64)
    data = JSONField(default={})

    class Meta:
        unique_together = (('test', 'key'),)

    def save(self, *args, **kwargs):
        self.build = self.test.build
        self.revision = self.build.revision
        self.project = self.revision.project
        super(TestData, self).save(*args, **kwargs)
