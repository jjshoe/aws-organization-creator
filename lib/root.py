import utils

def get_roots(**kwargs):
  return utils.get_results_from_paginator(client=kwargs['client'], api_call='list_roots', response_key='Roots')
