"""
This file is an intermediate layer between GitHub APIs and Django models.
"""

import requests

def request_github_issues(user, repo):
    """
    Returns a list of all the issues of a repository in `json` format.
    """
    try:
        api_data = 'https://api.github.com/repos/'+ user +'/' + repo + '/issues?state=all'
        response = requests.get(api_data)
        if response.status_code < 400:
            return {'error': False, 'data': response.json(), 'status_code': response.status_code}
        else:
            return {'error': True, 'data': response.json(), 'status_code': response.status_code}
    except:
        return {'error': True, 'data': 'There is no Internet connection'}
