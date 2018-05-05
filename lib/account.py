import time
import utils

import pprint
pp = pprint.PrettyPrinter(indent=4)

# Gets an account
def get_account(**kwargs):
  try:
    accounts=[]
    if 'parent_id' in kwargs:
      accounts = utils.get_results_from_paginator(client=kwargs['client'], api_call='list_accounts_for_parent', response_key='Accounts', args={'ParentId': kwargs['parent_id']})
    else:
      accounts = utils.get_results_from_paginator(client=kwargs['client'], api_call='list_accounts', response_key='Accounts')
    for account in accounts:
      if account['Email'] == kwargs['email']:
        return account
  except Exception as exception:
    utils.handle_exception(friendly_description='Unable to get account', exception=exception)

# Creates an AWS account
def create_account(**kwargs):
  try:
    response = kwargs['client'].create_account(Email=kwargs['account_email'], AccountName=kwargs['account_name'], IamUserAccessToBilling='ALLOW')
    return response
  except Exception as exception:
    utils.handle_exception(friendly_description='Unable to create accounts', exception=exception)

def move_account_to_organization_unit(**kwargs):
  print('Moving account %s (%s, %s) from under %s (%s) to under %s (%s)' % (kwargs['account_name'], kwargs['account_email'], kwargs['account_id'], kwargs['source_parent_name'], kwargs['source_parent_id'], kwargs['destination_parent_name'], kwargs['destination_parent_id']))
  parent_accounts = None
  try:
    parent_accounts = kwargs['client'].list_parents(ChildId=kwargs['account_id'])
  except Exception as exception:
    utils.handle_exception(friendly_description='Unable to list parents of the account', exception=exception)
  if parent_accounts['Parents'][0]['Id'] == kwargs['destination_parent_id']:
    print('Account %s (%s, %s) is already under %s (%s)' % (kwargs['account_name'], kwargs['account_email'], kwargs['account_id'], kwargs['destination_parent_name'], kwargs['destination_parent_id']))
  else:
    try:
      kwargs['client'].move_account(SourceParentId=parent_accounts['Parents'][0]['Id'], DestinationParentId=kwargs['destination_parent_id'], AccountId=kwargs['account_id'])
      print('Moved account %s (%s, %s) is under %s (%s)' % (kwargs['account_name'], kwargs['account_email'], kwargs['account_id'], kwargs['destination_parent_name'], kwargs['destination_parent_id']))
    except Exception as exception:
      utils.handle_exception(friendly_description='Unable to move the account under an organizational unit', exception=exception)

def create_account_status(**kwargs):
  while True:
    try:
      response = kwargs['client'].describe_create_account_status(CreateAccountRequestId=kwargs['create_account_request_id'])
      if response['CreateAccountStatus']['State'] == 'SUCCEEDED':
        print('%s (%s) created.' % (kwargs['account_name'], response['CreateAccountStatus']['AccountId']))
        return response['CreateAccountStatus']['AccountId']
      elif response['CreateAccountStatus']['State'] == 'FAILED' and response['CreateAccountStatus']['FailureReason'] == 'EMAIL_ALREADY_EXISTS':
        response = get_account(client=kwargs['client'], email=kwargs['account_email'])
        print('Account %s (%s, %s) already exists.' % (kwargs['account_name'], kwargs['account_email'], response['Id']))
        return response['Id']
      elif response['CreateAccountStatus']['State'] == 'FAILED':
        print('%s failed to be created: %s' % (kwargs['account_name'], response['CreateAccountStatus']['FailureReason']))
        exit(1)
      else:
        print('Waiting for account %s to be created' % (kwargs['account_name']))
        time.sleep(2)
    except Exception as exception:
      utils.handle_exception(friendly_description='Unable to check account creation status', exception=exception)
