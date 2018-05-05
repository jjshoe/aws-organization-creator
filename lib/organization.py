import utils

# There is only a single organization in AWS

# Return information on the single organization
def get_organization(**kwargs):
  try:
    response = kwargs['client'].describe_organization()
    return response['Organization']
  except Exception as exception:
    utils.handle_exception(friendly_description='Unable to list root organizational units', exception=exception)

# Create the single organization
def create_organization(**kwargs):
  try:
    response = kwargs['client'].create_organization(FeatureSet=kwargs['FeatureSet'])
    print('Created organization')
    return response
  except kwargs['client'].exceptions.AlreadyInOrganizationException as exception:
    print('A root organization was already made')
    return kwargs['client'].describe_organization()
  except Exception as exception:
    utils.handle_exception(friendly_description='Unable to make an organization', exception=exception)
