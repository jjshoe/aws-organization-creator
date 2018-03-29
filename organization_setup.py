#!/usr/bin/env python

import boto3
import botocore
import os
import time
import traceback
import yaml

import pprint
pp = pprint.PrettyPrinter(indent=4)

# Handle exceptions
def handle_exception(**kwargs):
  print(kwargs['friendly_description'])
  print(kwargs['exception'])
  if 'VERBOSE' in os.environ:
    traceback.print_exc()
  exit(1)

# Find depth of a hash
def organization_depth(**kwargs):
  for item in kwargs['children']:
    found_organizational_unit = 0
    for key, value in item.iteritems():
      if key == 'organizational_unit':
        found_organizational_unit = 1
      if key == 'children':
        return organization_depth(children=item['children'], count=kwargs['count']) + 1
  return found_organizational_unit

# Get the root aws organization, right now AWS only lets you have one,a nd you can't name it
def get_organization(**kwargs):
  try:
    return kwargs['client'].list_roots()
  except Exception as exception:
    handle_exception(friendly_description='Unable to list root organizational units', exception=exception)

# Get an account from an email address and parent organization/organizational unit
def get_account_from_organizations(**kwargs):
  try:
    response = kwargs['client'].list_accounts()
    for account in response['Accounts']:
      if account['Email'] == kwargs['email']:
        return account['Id']
    return None
  except Exception as exception:
    handle_exception(friendly_description='Unable to list root organizational units', exception=exception)

# Get an organization/organizational unit friendly name
def get_organization_name(**kwargs):
  try:
    if kwargs['id'].startswith('r-'):
      return 'Root'
    elif kwargs['id'].startswith('ou-'):
      response = kwargs['client'].describe_organizational_unit(OrganizationalUnitId=kwargs['id'])
      return response['OrganizationalUnit']['Name']
    else:
      return 'Unknown'
  except Exception as exception:
    handle_exception(friendly_description='Unable to get the organization/organizational unit name', exception=exception)

# Get an organizational unit id from friendly name
def get_organizationl_unit_id_from_friendly_name(**kwargs):
  try:
    response = kwargs['client'].list_organizational_units_for_parent(ParentId=kwargs['id'])

    for organizational_unit in response['OrganizationalUnits']:
      if organizational_unit['Name'] == kwargs['name']:
        return organizational_unit['Id']
    return None
  except Exception as exception:
    handle_exception(friendly_description='Unable to get the organizational unit id from the friendly name', exception=exception)

# AWS limits you right now to one root organization, this creates that for you, no name can be passed in
def create_organization(**kwargs):
  try:
    response = kwargs['client'].create_organization(FeatureSet=kwargs['FeatureSet'])
    return response
  except client.exceptions.AlreadyInOrganizationException as exception:
    print('A root organization was already made')
    return kwargs['client'].describe_organization()
  except Exception as exception:
    handle_exception(friendly_description='Unable to make an organization', exception=exception)

# Create AWS organizational units inside the master account
def create_organization_units(**kwargs):
  try:
    for item in kwargs['organizations']:
      parent_id = kwargs['parent_id']

      if 'organizational_unit' in item:
        parent_name = get_organization_name(client=kwargs['client'], id=kwargs['parent_id'])
        print('Creating organizational unit %s with parent %s (%s)' % (item['organizational_unit'], parent_name, kwargs['parent_id']))

        try:
          response = kwargs['client'].create_organizational_unit(ParentId=kwargs['parent_id'], Name=item['organizational_unit'])
          parent_id = response['OrganizationalUnit']['Id']
        except client.exceptions.DuplicateOrganizationalUnitException as exception:
          print('Organization %s already exists under parent %s (%s)' % (item['organizational_unit'], parent_name, kwargs['parent_id']))
          parent_id = get_organizationl_unit_id_from_friendly_name(client=client, id=kwargs['parent_id'], name=item['organizational_unit'])
      if 'children' in item and parent_id:
        create_organization_units(client=client, parent_id=parent_id, organizations=item['children'])
      if 'account_name' in item and parent_id:
        # Create account
        parent_name = get_organization_name(client=kwargs['client'], id=kwargs['parent_id'])
        print('Creating account %s (%s) with parent %s (%s)' % (item['account_name'], item['account_email'], parent_name, parent_id))
        response = create_account(client=kwargs['client'], account_name=item['account_name'], account_email=item['account_email'])

        # Verify account created
        account_id = check_status(client=kwargs['client'], id=response['CreateAccountStatus']['Id'], account_name=item['account_name'], account_email=item['account_email'], parent_id=kwargs['parent_id'])

        # Move account into the organizational unit
        print('Moving account %s (%s, %s) under organizational unit %s (%s)' % (item['account_name'], item['account_email'], account_id, parent_name, parent_id))
        organization = get_organization(client=client)
        move_account_to_organizational_unit(client=kwargs['client'], source_parent_id=organization['Roots'][0]['Id'], destination_parent_id=parent_id, account_id=account_id, account_name=item['account_name'], account_email=item['account_email'])
  except Exception as exception:
    handle_exception(friendly_description='Unable to make an organizational unit', exception=exception)

# Creates an AWS account
def create_account(**kwargs):
  try:
   response = kwargs['client'].create_account(Email=kwargs['account_email'], AccountName=kwargs['account_name'], IamUserAccessToBilling='ALLOW')
   return response
  except Exception as exception:
    handle_excpetion(friendly_description='Unable to create accounts', exception=exception)

# Move an AWS account under an organizational unit
#
# This singular function has a terrible error if the account is already in place, it says
# 'An error occurred (AccountNotFoundException) when calling the MoveAccount operation: You specified an account that doesn't exist.'
# So though the account exists, and is in the correct OU, we have to specifically check for this, so we can return a sane error
#
def move_account_to_organizational_unit(**kwargs):
  try:
    response = kwargs['client'].list_accounts_for_parent(ParentId=kwargs['destination_parent_id'])
    for account in response['Accounts']:
      if account['Id'] == kwargs['account_id']:
        parent_name = get_organization_name(client=client, id=kwargs['destination_parent_id'])
        print('Account %s (%s %s) is already under parent %s (%s)' % (kwargs['account_name'], kwargs['account_email'], kwargs['account_id'], parent_name, kwargs['destination_parent_id']))
        return
  except Exception as exception:
    handle_exception(friendly_description='Unable to get a list of accounts under a parent when seeing if we should move an account', exception=exception)
  try:
    kwargs['client'].move_account(SourceParentId=kwargs['source_parent_id'], DestinationParentId=kwargs['destination_parent_id'], AccountId=kwargs['account_id'])
  except Exception as exception:
    handle_exception(friendly_description='Unable to move the account under an organizational unit', exception=exception)

# Check to see if we're waiting on any accounts to create, give us a reason if creation fails
def check_status(**kwargs):
  while True:
    response = kwargs['client'].describe_create_account_status(CreateAccountRequestId=kwargs['id'])
    if response['CreateAccountStatus']['State'] == 'SUCCEEDED':
      print('%s (%s) created.' % (kwargs['account_name'], response['CreateAccountStatus']['AccountId']))
      return response['CreateAccountStatus']['AccountId']
    elif response['CreateAccountStatus']['State'] == 'FAILED' and response['CreateAccountStatus']['FailureReason'] == 'EMAIL_ALREADY_EXISTS':
      account_id = get_account_from_organizations(client=client, email=kwargs['account_email'])
      parent_name = get_organization_name(client=client, id=kwargs['parent_id'])
      print('Account %s (%s, %s) already exists.' % (kwargs['account_name'], kwargs['account_email'], account_id))
      return account_id
    elif response['CreateAccountStatus']['State'] == 'FAILED':
      print('%s failed to be created: %s' % (kwargs['account_name'], response['CreateAccountStatus']['FailureReason']))
      exit(1)
    else:
      print('Waiting for account %s to be created' % (kwargs['account_name']))
      time.sleep(2)

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
    data = yaml.load(raw_yaml)
  except yaml.YAMLError as exception:
    handle_exception(friendly_desription='Trouble parsing settings.yml', expcetion=exception)

  # Validate that our organization structure isn't more than five deep (AWS limit)
  if organization_depth(children=data, count=1) > 5:
    print('You are limited to no more than five organizational units deep')
    exit(1)

  # Create the organization in the main account
  organization = create_organization(client=client, FeatureSet='ALL')

  # Get the initial parent organizational unit id (In this case it's the root unit made up above)
  organization = get_organization(client=client)

  # Create all organizational units and accounts underneath them
  create_organization_units(client=client, organizations=data, parent_id=organization['Roots'][0]['Id'])
