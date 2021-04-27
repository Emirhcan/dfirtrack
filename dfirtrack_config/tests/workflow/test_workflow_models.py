from django.test import TestCase
from dfirtrack_config.models import Workflow, WorkflowDefaultArtifactname
from dfirtrack_main.models import System, Systemstatus, Task, Taskname
from dfirtrack_artifacts.models import Artifact, Artifacttype
from django.contrib.auth.models import User
from django.utils import timezone

class WorkflowModelTestCase(TestCase):
    """ workflow model tests """

    @classmethod
    def setUpTestData(cls):

        # Create objects
        artifacttype_1 = Artifacttype.objects.create(artifacttype_name='artifacttype_1')
        taskname_1 = Taskname.objects.create(taskname_name='taskname_1')

        systemstatus = Systemstatus.objects.create(systemstatus_name='systemstatus_1')
        test_user = User.objects.create_user(username='testuser_workflow', password='QVe1EH1Z5MshOW2GHS4b')
        
        System.objects.create(
            system_name = 'system_1',
            systemstatus = systemstatus,
            system_modify_time = timezone.now(),
            system_created_by_user_id = test_user,
            system_modified_by_user_id = test_user,
        )

        # create objects
        workflow_task = Workflow.objects.create(
            workflow_name='workflow_task',
            workflow_created_by_user_id = test_user,
            workflow_modified_by_user_id = test_user,
        )
        workflow_task.tasknames.set((taskname_1,))

        workflow_artifact = Workflow.objects.create(
            workflow_name='workflow_artifact',
            workflow_created_by_user_id = test_user,
            workflow_modified_by_user_id = test_user,
        )
        artifacttypedefaultnames = WorkflowDefaultArtifactname.objects.create(workflow=workflow_artifact, artifacttype=artifacttype_1, artifact_default_name='artifact_default_name_1')

    ''' test model methods '''

    def test_workflow_string(self):
        # get object
        workflow = Workflow.objects.get(workflow_name='workflow_task')
        # compare
        self.assertEqual(str(workflow), 'workflow_task')

    def test_workflow_name_length(self):
        # get object
        workflow = Workflow.objects.get(workflow_name='workflow_task')
        # get max length
        max_length = workflow._meta.get_field('workflow_name').max_length
        # compare
        self.assertEqual(max_length, 50)

    def test_workflow_get_absolute_url(self):
        # get object
        workflow = Workflow.objects.get(workflow_id=1)
        # compare
        self.assertEqual(workflow.get_absolute_url(), '/config/workflow/1/')

    def test_workflow_get_update_url(self):
        # get object
        workflow = Workflow.objects.get(workflow_id=1)
        # compare
        self.assertEqual(workflow.get_update_url(), '/config/workflow/1/update/')

    def test_workflow_get_delete_url(self):        
        # get object
        workflow = Workflow.objects.get(workflow_id=1)
        # compare
        self.assertEqual(workflow.get_delete_url(), '/config/workflow/1/delete/')

    def helper_apply_workflow(self, system, workflow_name, workflow_amount):
        # get worklow
        workflow = Workflow.objects.get(workflow_name=workflow_name)
        # build workflow list
        workflows = [workflow.workflow_id for i in range(workflow_amount)]
        # get user
        user = User.objects.get(username='testuser_workflow')
        # apply workflow
        return Workflow.apply(workflows, system, user)

    def test_apply_workflow_task_creation(self):    
        # get object
        system = System.objects.get(system_id=1)
        # apply workflow
        error_code = self.helper_apply_workflow(system, 'workflow_task', 1)
        
        # get created taskeds for system
        task = Task.objects.get(system=system)
        # compare
        self.assertEqual(error_code, 0)        
        self.assertEqual(str(task.taskname), 'taskname_1')

    def test_apply_workflow_artifact_creation(self):
        # get object
        system = System.objects.get(system_id=1)
        # apply workflow
        error_code = self.helper_apply_workflow(system, 'workflow_artifact', 1)

        # get created artifacts for system
        artifact = Artifact.objects.get(system=system) 
        # compare
        self.assertEqual(error_code, 0)
        self.assertTupleEqual(
                (artifact.artifact_name, artifact.artifacttype.artifacttype_name),
                ('artifact_default_name_1', 'artifacttype_1')
        )

    def test_apply_multiple_workflows_task_creation(self):
        # get object
        system = System.objects.get(system_id=1)
        # apply workflow
        error_code = self.helper_apply_workflow(system, 'workflow_task', 2)  
        
        # get created taskeds for system
        tasks = Task.objects.filter(system=system)
        # compare
        self.assertEqual(error_code, 0)
        self.assertEqual(tasks.count(), 2)
        self.assertEqual(str(tasks[1].taskname), 'taskname_1')

    def test_apply_multiple_workflows_artifact_creation(self):
        # get object
        system = System.objects.get(system_id=1)
        # apply workflow
        error_code = self.helper_apply_workflow(system, 'workflow_artifact', 2)  

        artifacts = Artifact.objects.filter(system=system)
        # compare
        self.assertEqual(error_code, 0)
        self.assertEqual(artifacts.count(), 2)
        self.assertTupleEqual(
                (artifacts[1].artifact_name, artifacts[1].artifacttype.artifacttype_name),
                ('artifact_default_name_1', 'artifacttype_1')
        )

    def test_apply_nonexistent_workflow(self):
        # get object
        workflows = (99,)
        system = System.objects.get(system_id=1)
        user = User.objects.get(username='testuser_workflow')
        error_code = Workflow.apply(workflows, system, user)
        # compare
        self.assertEqual(error_code, 1)

    def test_apply_wrong_value_workflow(self):
        # get object
        workflows = ('should_be_integer',)
        system = System.objects.get(system_id=1)
        user = User.objects.get(username='testuser_workflow')
        error_code = Workflow.apply(workflows, system, user)
        # compare
        self.assertEqual(error_code, 1)

    ''' test model labels '''

    def helper_workflow_attribute_label(self, field, expected_label):
        # get object
        workflow = Workflow.objects.get(workflow_name='workflow_task')
        # get label
        field_label = workflow._meta.get_field(field).verbose_name
        # compare
        self.assertEqual(field_label, expected_label)

    def test_workflow_id_attribute_label(self):
        self.helper_workflow_attribute_label('workflow_id', 'workflow id')

    def test_workflow_tasknames_attribute_label(self):
        self.helper_workflow_attribute_label('tasknames', 'tasknames')
    
    def test_workflow_artifacttypes_attribute_label(self):
        self.helper_workflow_attribute_label('artifacttypes', 'artifacttypes')
    
    def test_workflow_name_attribute_label(self):
        self.helper_workflow_attribute_label('workflow_name', 'workflow name')

    def test_workflow_create_time_attribute_label(self):
        self.helper_workflow_attribute_label('workflow_create_time', 'workflow create time')

    def test_workflow_modify_time_attribute_label(self):
        self.helper_workflow_attribute_label('workflow_modify_time', 'workflow modify time')

    def test_workflow_created_by_user_id_attribute_label(self):
        self.helper_workflow_attribute_label('workflow_created_by_user_id', 'workflow created by user id')

    def test_workflow_modified_by_user_id_attribute_label(self):
        self.helper_workflow_attribute_label('workflow_modified_by_user_id', 'workflow modified by user id')