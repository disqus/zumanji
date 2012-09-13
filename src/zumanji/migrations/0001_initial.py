# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Project'
        db.create_table('zumanji_project', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('data', self.gf('django.db.models.fields.TextField')(default={})),
        ))
        db.send_create_signal('zumanji', ['Project'])

        # Adding model 'Revision'
        db.create_table('zumanji_revision', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['zumanji.Project'])),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('data', self.gf('django.db.models.fields.TextField')(default={})),
        ))
        db.send_create_signal('zumanji', ['Revision'])

        # Adding unique constraint on 'Revision', fields ['project', 'label']
        db.create_unique('zumanji_revision', ['project_id', 'label'])

        # Adding model 'Build'
        db.create_table('zumanji_build', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['zumanji.Project'])),
            ('revision', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['zumanji.Revision'])),
            ('datetime', self.gf('django.db.models.fields.DateTimeField')()),
            ('num_tests', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('total_duration', self.gf('django.db.models.fields.FloatField')(default=0.0)),
            ('data', self.gf('django.db.models.fields.TextField')(default={})),
            ('result', self.gf('django.db.models.fields.CharField')(max_length=16, null=True)),
        ))
        db.send_create_signal('zumanji', ['Build'])

        # Adding unique constraint on 'Build', fields ['revision', 'datetime']
        db.create_unique('zumanji_build', ['revision_id', 'datetime'])

        # Adding model 'BuildTag'
        db.create_table('zumanji_buildtag', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal('zumanji', ['BuildTag'])

        # Adding M2M table for field builds on 'BuildTag'
        db.create_table('zumanji_buildtag_builds', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('buildtag', models.ForeignKey(orm['zumanji.buildtag'], null=False)),
            ('build', models.ForeignKey(orm['zumanji.build'], null=False))
        ))
        db.create_unique('zumanji_buildtag_builds', ['buildtag_id', 'build_id'])

        # Adding model 'Test'
        db.create_table('zumanji_test', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['zumanji.Project'])),
            ('revision', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['zumanji.Revision'])),
            ('build', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['zumanji.Build'])),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['zumanji.Test'], null=True)),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True)),
            ('num_tests', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('mean_duration', self.gf('django.db.models.fields.FloatField')(default=0.0)),
            ('upper_duration', self.gf('django.db.models.fields.FloatField')(default=0.0)),
            ('lower_duration', self.gf('django.db.models.fields.FloatField')(default=0.0)),
            ('upper90_duration', self.gf('django.db.models.fields.FloatField')(default=0.0)),
            ('data', self.gf('django.db.models.fields.TextField')(default={})),
            ('result', self.gf('django.db.models.fields.CharField')(max_length=16, null=True)),
        ))
        db.send_create_signal('zumanji', ['Test'])

        # Adding unique constraint on 'Test', fields ['build', 'label']
        db.create_unique('zumanji_test', ['build_id', 'label'])

        # Adding model 'TestData'
        db.create_table('zumanji_testdata', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['zumanji.Project'])),
            ('revision', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['zumanji.Revision'])),
            ('build', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['zumanji.Build'])),
            ('test', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['zumanji.Test'])),
            ('key', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('data', self.gf('django.db.models.fields.TextField')(default={})),
        ))
        db.send_create_signal('zumanji', ['TestData'])

        # Adding unique constraint on 'TestData', fields ['test', 'key']
        db.create_unique('zumanji_testdata', ['test_id', 'key'])


    def backwards(self, orm):
        # Removing unique constraint on 'TestData', fields ['test', 'key']
        db.delete_unique('zumanji_testdata', ['test_id', 'key'])

        # Removing unique constraint on 'Test', fields ['build', 'label']
        db.delete_unique('zumanji_test', ['build_id', 'label'])

        # Removing unique constraint on 'Build', fields ['revision', 'datetime']
        db.delete_unique('zumanji_build', ['revision_id', 'datetime'])

        # Removing unique constraint on 'Revision', fields ['project', 'label']
        db.delete_unique('zumanji_revision', ['project_id', 'label'])

        # Deleting model 'Project'
        db.delete_table('zumanji_project')

        # Deleting model 'Revision'
        db.delete_table('zumanji_revision')

        # Deleting model 'Build'
        db.delete_table('zumanji_build')

        # Deleting model 'BuildTag'
        db.delete_table('zumanji_buildtag')

        # Removing M2M table for field builds on 'BuildTag'
        db.delete_table('zumanji_buildtag_builds')

        # Deleting model 'Test'
        db.delete_table('zumanji_test')

        # Deleting model 'TestData'
        db.delete_table('zumanji_testdata')


    models = {
        'zumanji.build': {
            'Meta': {'unique_together': "(('revision', 'datetime'),)", 'object_name': 'Build'},
            'data': ('django.db.models.fields.TextField', [], {'default': '{}'}),
            'datetime': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_tests': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['zumanji.Project']"}),
            'result': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True'}),
            'revision': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['zumanji.Revision']"}),
            'total_duration': ('django.db.models.fields.FloatField', [], {'default': '0.0'})
        },
        'zumanji.buildtag': {
            'Meta': {'object_name': 'BuildTag'},
            'builds': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'tags'", 'symmetrical': 'False', 'to': "orm['zumanji.Build']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'zumanji.project': {
            'Meta': {'object_name': 'Project'},
            'data': ('django.db.models.fields.TextField', [], {'default': '{}'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        },
        'zumanji.revision': {
            'Meta': {'unique_together': "(('project', 'label'),)", 'object_name': 'Revision'},
            'data': ('django.db.models.fields.TextField', [], {'default': '{}'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['zumanji.Project']"})
        },
        'zumanji.test': {
            'Meta': {'unique_together': "(('build', 'label'),)", 'object_name': 'Test'},
            'build': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['zumanji.Build']"}),
            'data': ('django.db.models.fields.TextField', [], {'default': '{}'}),
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
            'data': ('django.db.models.fields.TextField', [], {'default': '{}'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['zumanji.Project']"}),
            'revision': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['zumanji.Revision']"}),
            'test': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['zumanji.Test']"})
        }
    }

    complete_apps = ['zumanji']