from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dfirtrack_artifacts', '0005_values_artifactpriority'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('dfirtrack_main', '0014_case_expansion'),
        ('dfirtrack_config', '0015_mainconfigmodel_casestatus'),
    ]

    operations = [
        migrations.CreateModel(
            name='Workflow',
            fields=[
                ('workflow_id', models.AutoField(primary_key=True, serialize=False)),
                ('workflow_name', models.CharField(max_length=50, unique=True)),
                ('workflow_create_time', models.DateTimeField(auto_now_add=True)),
                ('workflow_modify_time', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='WorkflowDefaultArtifactname',
            fields=[
                ('workflow_default_artifactname_id', models.AutoField(primary_key=True, serialize=False)),
                ('artifact_default_name', models.CharField(max_length=50)),
                ('artifacttype', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='workflow_artifacttype_mapping', to='dfirtrack_artifacts.artifacttype')),
                ('workflow', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='workflow_mapping', to='dfirtrack_config.workflow')),
            ],
        ),
        migrations.AddField(
            model_name='workflow',
            name='artifacttypes',
            field=models.ManyToManyField(blank=True, related_name='main_config_workflow_artifacttype', through='dfirtrack_config.WorkflowDefaultArtifactname', to='dfirtrack_artifacts.Artifacttype'),
        ),
        migrations.AddField(
            model_name='workflow',
            name='tasknames',
            field=models.ManyToManyField(blank=True, related_name='main_config_workflow_taskname', to='dfirtrack_main.Taskname'),
        ),
        migrations.AddField(
            model_name='workflow',
            name='workflow_created_by_user_id',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='workflow_created_by', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='workflow',
            name='workflow_modified_by_user_id',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='worklfow_modified_by', to=settings.AUTH_USER_MODEL),
        ),
    ]
