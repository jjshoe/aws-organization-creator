import json
import utils

# Enable any specific policy type
def enable_service_control_policy(**kwargs):
  try:
    kwargs['client'].enable_policy_type(RootId=kwargs['root_id'], PolicyType='SERVICE_CONTROL_POLICY')
    print('Enabled service control policy SERVICE_CONTROL_POLICY')
  except kwargs['client'].exceptions.PolicyTypeAlreadyEnabledException as exception:
    print('Service control policy SERVICE_CONTROL_POLICY is already enabled')
  except Exception as exception:
    utils.handle_exception(friendly_description='Unable to enable policy type SERVICE_CONTROL_POLICY', exception=exception)

# Create a service control policy
def create_service_control_policy(**kwargs):
  try:
    name = kwargs['service_control_policy']['name']
    description = kwargs['service_control_policy']['description']
    policy = kwargs['service_control_policy']['policy']
    response = kwargs['client'].create_policy(Type='SERVICE_CONTROL_POLICY', Name=name, Description=description, Content=json.dumps(policy))
    return response['Policy']['PolicySummary']
  except kwargs['client'].exceptions.DuplicatePolicyException as exception:
    # find the policy and return what we know about it
    print('Service control policy %s already exists' % (name))
    response = utils.get_results_from_paginator(client=kwargs['client'], api_call='list_policies', response_key='Policies', args={'Filter': 'SERVICE_CONTROL_POLICY'})
    for policy in response:
      if policy['Name'] == name:
        return policy
  except Exception as exception:
    utils.handle_exception(friendly_description='Unable to make a service control policy', exception=exception)

# Attach the policy to a target. 
# A target can be a root, organization unit, or account
def attach_service_control_policy(**kwargs):
  try:
    print('Attaching policy %s (%s) to %s (%s)' % (kwargs['policy_name'], kwargs['policy_id'], kwargs['target_name'], kwargs['target_id']))
    kwargs['client'].attach_policy(PolicyId=kwargs['policy_id'], TargetId=kwargs['target_id'])
  except kwargs['client'].exceptions.DuplicatePolicyAttachmentException as exception:
    print('Policy %s (%s) is already attached to %s (%s)' % (kwargs['policy_name'], kwargs['policy_id'], kwargs['target_name'], kwargs['target_id']))
  except Exception as exception:
    utils.handle_exception(friendly_description='Unable to attach a service control policy', exception=exception)

