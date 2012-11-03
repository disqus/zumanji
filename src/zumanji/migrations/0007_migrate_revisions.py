# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models
from django.db.models import F

class Migration(DataMigration):

    def forwards(self, orm):
        for build in orm['zumanji.Build'].objects.all():
            orm['zumanji.BuildRevision'].objects.create(
                build=build,
                project=build.project,
                revision_label=build.revision.label,
            )

    def backwards(self, orm):
        # probably a bad idea
        orm['zumanji.BuildRevision'].objects.all().delete()

    models = {
        'zumanji.build': {
            'Meta': {'unique_together': "(('revision', 'datetime'),)", 'object_name': 'Build'},
            'data': ('django.db.models.fields.TextField', [], {'default': '{}', 'blank': 'True'}),
            'datetime': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_tests': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['zumanji.Project']"}),
            'result': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True'}),
            'revision': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['zumanji.Revision']"}),
            'total_duration': ('django.db.models.fields.FloatField', [], {'default': '0.0'})
        },
        'zumanji.buildrevision': {
            'Meta': {'unique_together': "(('build', 'revision_label'),)", 'object_name': 'BuildRevision'},
            'build': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['zumanji.Build']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['zumanji.Project']"}),
            'revision_label': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True'})
        },
        'zumanji.buildtag': {
            'Meta': {'object_name': 'BuildTag'},
            'builds': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'tags'", 'symmetrical': 'False', 'to': "orm['zumanji.Build']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'zumanji.project': {
            'Meta': {'object_name': 'Project'},
            'data': ('django.db.models.fields.TextField', [], {'default': '{}', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64'})
        },
        'zumanji.revision': {
            'Meta': {'unique_together': "(('project', 'label'),)", 'object_name': 'Revision'},
            'data': ('django.db.models.fields.TextField', [], {'default': '{}', 'blank': 'True'}),
            'datetime': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'num_builds': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['zumanji.Project']"})
        },
        'zumanji.revisionparent': {
            'Meta': {'unique_together': "(('project', 'revision_label', 'parent_label'),)", 'object_name': 'RevisionParent'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'parent_label': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['zumanji.Project']"}),
            'revision_label': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True'})
        },
        'zumanji.test': {
            'Meta': {'unique_together': "(('build', 'label'),)", 'object_name': 'Test'},
            'build': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['zumanji.Build']"}),
            'data': ('django.db.models.fields.TextField', [], {'default': '{}', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'lower_duration': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'mean_duration': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'num_tests': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['zumanji.Test']", 'null': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['zumanji.Project']"}),
            'result': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True'}),
            'revision': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['zumanji.Revision']"}),
            'upper90_duration': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'upper_duration': ('django.db.models.fields.FloatField', [], {'default': '0.0'})
        },
        'zumanji.testdata': {
            'Meta': {'unique_together': "(('test', 'key'),)", 'object_name': 'TestData'},
            'build': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['zumanji.Build']"}),
            'data': ('django.db.models.fields.TextField', [], {'default': '{}', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['zumanji.Project']"}),
            'revision': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['zumanji.Revision']"}),
            'test': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['zumanji.Test']"})
        }
    }

    complete_apps = ['zumanji']
    symmetrical = True
