#!/usr/bin/env python

import boto3
import botocore
import lib.account
import lib.organization
import lib.organization_unit
import lib.root
import lib.service_control_policy
import lib.utils
import os
import time
import traceback
import json
import yaml

import pprint
pp = pprint.PrettyPrinter(indent=4)

# Create all child elements, which includes orgnaization units, accounts, and service control policies 
def create_child_elements(**kwargs):
  try:
    for item in kwargs['organizations']:
      parent_id=kwargs['parent_id']
      parent_name=kwargs['parent_name']
      # Create organization units
      if 'organization_unit' in item:
        response = lib.organization_unit.create_organization_unit(client=kwargs['client'], parent_id=kwargs['parent_id'], parent_name=kwargs['parent_name'], organization_unit=item['organization_unit'])
        parent_id = response['id']
        parent_name = response['name']
      # Create and attach service control policies 
      if 'service_control_policy' in item and parent_id:
        policy = lib.service_control_policy.create_service_control_policy(client=client, service_control_policy=item['service_control_policy'])
        lib.service_control_policy.attach_service_control_policy(client=client, target_id=parent_id, target_name=parent_name, policy_id=policy['Id'], policy_name=policy['Name'])
      # Create accounts, and move them into the orgnaization unit
      if 'account_name' in item and parent_id:
        response = lib.account.create_account(client=kwargs['client'], account_name=item['account_name'], account_email=item['account_email'])
        account_id = lib.account.create_account_status(client=kwargs['client'], create_account_request_id=response['CreateAccountStatus']['Id'], parent_id=parent_id, account_name=item['account_name'], account_email=item['account_email'])
        lib.account.move_account_to_organization_unit(client=kwargs['client'], source_parent_id=kwargs['root_id'], source_parent_name='Root', destination_parent_id=parent_id, destination_parent_name=parent_name, account_id=account_id, account_name=item['account_name'], account_email=item['account_email'])

      # Go down a step in the XML, and call back into this function with all the children
      if 'children' in item and parent_id and parent_name:
        create_child_elements(client=kwargs['client'], root_id=kwargs['root_id'], parent_id=parent_id, parent_name=parent_name, organizations=item['children'])
  except Exception as exception:
    lib.utils.handle_exception(friendly_description='Unable to create children', exception=exception)

if __name__ == '__main__':
  # Creating a client to communicate with the AWS API about organizations
  try:
    client = boto3.client('organizations')
  except client.exceptions.ClientError as exception:
    handle_exception(friendly_description='Trouble connecting an API client to talk to organizations', exception=exception)

  # Read in our yaml file
  file = open(os.path.dirname(os.path.realpath(__file__)) + '/settings.yml', 'r') 
  raw_yaml = file.read()
  file.close()

  # Parse the yaml file to a useful datastructure, give us a reason if that parsing fails
  try:
    data = yaml.load(raw_yaml, Loader=yaml.BaseLoader)
  except yaml.YAMLError as exception:
    handle_exception(friendly_desription='Trouble parsing settings.yml', expcetion=exception)

  # Validate that our organization structure isn't more than five deep (AWS limit)
  if lib.utils.organization_depth(children=data, count=1) > 5:
    print('You are limited to no more than five organizational units deep')
    exit(1)

  # Create the organization in the main account
  # only one can be made, though someday this may be expanded, we ignore the top level org name in the settings file
  organization = lib.organization.create_organization(client=client, FeatureSet='ALL')

  # Enable service control policies
  # This simply gives you the ability to use service control policies in the org, nothing more.
  roots = lib.root.get_roots(client=client)
  lib.service_control_policy.enable_service_control_policy(client=client, root_id=roots[0]['Id'])

  # If a service account policy has been defined for the root, we need to make the policy, and attach it to the root
  # This only happens for the root here, it will happen again in the create_child_elements function as well
  if 'service_control_policy' in data[0]:
    policy = lib.service_control_policy.create_service_control_policy(client=client, target_id=roots[0]['Id'], service_control_policy=data[0]['service_control_policy'])
    lib.service_control_policy.attach_service_control_policy(client=client, target_id=roots[0]['Id'], target_name=roots[0]['Name'], policy_id=policy['Id'], policy_name=policy['Name'])

  # Create all organizational units and accounts underneath them
  create_child_elements(client=client, organizations=data[0]['children'], root_id=roots[0]['Id'], parent_id=roots[0]['Id'], parent_name='Root')
