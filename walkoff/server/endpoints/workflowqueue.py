from collections import OrderedDict

from flask import request, current_app
from flask_jwt_extended import jwt_required
from sqlalchemy import exists

from walkoff import executiondb
from walkoff.executiondb.argument import Argument
from walkoff.executiondb.workflow import Workflow
from walkoff.executiondb.workflowresults import WorkflowStatus, WorkflowStatusEnum
from walkoff.helpers import InvalidArgument
from walkoff.security import permissions_accepted_for_resources, ResourcePermissions
from walkoff.server.decorators import with_resource_factory, validate_resource_exists_factory, is_valid_uid
from walkoff.server.problem import Problem
from walkoff.server.returncodes import *


def does_workflow_exist(workflow_id):
    return executiondb.execution_db.session.query(exists().where(Workflow.id == workflow_id)).scalar()


def does_execution_id_exist(execution_id):
    return executiondb.execution_db.session.query(exists().where(WorkflowStatus.execution_id == execution_id)).scalar()


def workflow_status_getter(execution_id):
    return executiondb.execution_db.session.query(WorkflowStatus).filter_by(execution_id=execution_id).first()


with_workflow_status = with_resource_factory('workflow', workflow_status_getter, validator=is_valid_uid)
validate_workflow_is_registered = validate_resource_exists_factory('workflow', does_workflow_exist)
validate_execution_id_is_registered = validate_resource_exists_factory('workflow', does_execution_id_exist)

status_order = OrderedDict(
    [((WorkflowStatusEnum.running, WorkflowStatusEnum.awaiting_data, WorkflowStatusEnum.paused),
      WorkflowStatus.started_at),
     ((WorkflowStatusEnum.aborted, WorkflowStatusEnum.completed), WorkflowStatus.completed_at)])

executing_statuses = (WorkflowStatusEnum.running, WorkflowStatusEnum.awaiting_data, WorkflowStatusEnum.paused)
completed_statuses = (WorkflowStatusEnum.aborted, WorkflowStatusEnum.completed)


def get_all_workflow_status(limit=50):
    @jwt_required
    @permissions_accepted_for_resources(ResourcePermissions('playbooks', ['read']))
    def __func():
        ret = executiondb.execution_db.session.query(WorkflowStatus). \
            filter(WorkflowStatus.status.in_(executing_statuses)). \
            order_by(WorkflowStatus.started_at). \
            all()

        if len(ret) < limit:
            ret.extend(executiondb.execution_db.session.query(WorkflowStatus).
                       filter(WorkflowStatus.status.in_(completed_statuses)).
                       order_by(WorkflowStatus.started_at).
                       limit(limit - len(ret)).
                       all())

        ret = [workflow_status.as_json() for workflow_status in ret]
        return ret, SUCCESS

    return __func()


def get_workflow_status(execution_id):
    @jwt_required
    @permissions_accepted_for_resources(ResourcePermissions('playbooks', ['read']))
    @with_workflow_status('control', execution_id)
    def __func(workflow_status):
        return workflow_status.as_json(full_actions=True), SUCCESS

    return __func()


def execute_workflow():
    from walkoff.server.context import running_context

    data = request.get_json()
    workflow_id = data['workflow_id']

    @jwt_required
    @permissions_accepted_for_resources(ResourcePermissions('playbooks', ['execute']))
    @validate_workflow_is_registered('execute', workflow_id)
    def __func():
        args = data['arguments'] if 'arguments' in data else None
        start = data['start'] if 'start' in data else None

        arguments = []
        if args:
            try:
                arguments = [Argument(**arg) for arg in args]
            except InvalidArgument as e:
                current_app.logger.error('Could not execute workflow. Invalid Argument construction')
                return Problem(
                    INVALID_INPUT_ERROR,
                    'Cannot execute workflow.',
                    'An argument is invalid. Reason: {}'.format(e.message))

        execution_id = running_context.executor.execute_workflow(workflow_id, start=start, start_arguments=arguments)
        current_app.logger.info('Executed workflow {0}'.format(workflow_id))
        return {'id': execution_id}, SUCCESS_ASYNC

    return __func()


def control_workflow():
    from walkoff.server.context import running_context

    data = request.get_json()
    execution_id = data['execution_id']

    @jwt_required
    @permissions_accepted_for_resources(ResourcePermissions('playbooks', ['execute']))
    @validate_execution_id_is_registered('control', execution_id)
    def __func():
        status = data['status']

        if status == 'pause':
            running_context.executor.pause_workflow(execution_id)
        elif status == 'resume':
            running_context.executor.resume_workflow(execution_id)
        elif status == 'abort':
            running_context.executor.abort_workflow(execution_id)

        return None, NO_CONTENT

    return __func()
