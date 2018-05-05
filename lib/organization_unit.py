import utils

def create_organization_unit(**kwargs):
  print('Creating organizational unit %s with parent %s (%s)' % (kwargs['organization_unit'], kwargs['parent_name'], kwargs['parent_id']))
  try:
    response = kwargs['client'].create_organizational_unit(ParentId=kwargs['parent_id'], Name=kwargs['organization_unit'])
    return {'id': response['OrganizationalUnit']['Id'], 'name': response['OrganizationalUnit']['Name']}
  except kwargs['client'].exceptions.DuplicateOrganizationalUnitException as exception:
    print('Organization %s already exists under parent %s (%s)' % (kwargs['organization_unit'], kwargs['parent_name'], kwargs['parent_id']))
    organization_unit = get_organization_unit_from_name(client=kwargs['client'], id=kwargs['parent_id'], name=kwargs['organization_unit'])
    return {'id': organization_unit['Id'], 'name': organization_unit['Name']}

def get_organization_unit_from_name(**kwargs):
  response = utils.get_results_from_paginator(client=kwargs['client'], api_call='list_organizational_units_for_parent', response_key='OrganizationalUnits', args={'ParentId': kwargs['id']})
  for organization_unit in response:
    if organization_unit['Name'] == kwargs['name']:
      return organization_unit
