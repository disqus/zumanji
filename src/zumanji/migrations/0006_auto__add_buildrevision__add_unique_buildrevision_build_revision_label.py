# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'BuildRevision'
        db.create_table('zumanji_buildrevision', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['zumanji.Project'])),
            ('build', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['zumanji.Build'])),
            ('revision_label', self.gf('django.db.models.fields.CharField')(max_length=64, null=True)),
        ))
        db.send_create_signal('zumanji', ['BuildRevision'])

        # Adding unique constraint on 'BuildRevision', fields ['build', 'revision_label']
        db.create_unique('zumanji_buildrevision', ['build_id', 'revision_label'])

        # Adding field 'Revision.num_builds'
        db.add_column('zumanji_revision', 'num_builds',
                      self.gf('django.db.models.fields.PositiveIntegerField')(default=0),
                      keep_default=False)


    def backwards(self, orm):
        # Removing unique constraint on 'BuildRevision', fields ['build', 'revision_label']
        db.delete_unique('zumanji_buildrevision', ['build_id', 'revision_label'])

        # Deleting model 'BuildRevision'
        db.delete_table('zumanji_buildrevision')

        # Deleting field 'Revision.num_builds'
        db.delete_column('zumanji_revision', 'num_builds')


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