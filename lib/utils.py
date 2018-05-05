import os
import traceback

# Handle exceptions
def handle_exception(**kwargs):
  print(kwargs['friendly_description'])
  print(kwargs['exception'])
  if 'QUIET' not in os.environ:
    traceback.print_exc()
  exit(1)

# Find depth of our organization strucrture
def organization_depth(**kwargs):
  for item in kwargs['children']:
    found_organizational_unit = 0
    for key, value in item.iteritems():
      if key == 'organizational_unit':
        found_organizational_unit = 1
      if key == 'children':
        return organization_depth(children=item['children'], count=kwargs['count']) + 1
  return found_organizational_unit

# Wrap boto's paginator in niceties returning an array
def get_results_from_paginator(**kwargs):
  results = []
  paginator = kwargs['client'].get_paginator(kwargs['api_call'])
  page_iterator = None
  if 'args' in kwargs:
    page_iterator = paginator.paginate(**kwargs['args'])
  else:
    page_iterator = paginator.paginate()

  for page in page_iterator:
    for item in page[kwargs['response_key']]:
      results.append(item)
  return results

