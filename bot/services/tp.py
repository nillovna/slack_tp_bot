from sanic import response
from sanic.response import json
import config
import requests
import re
from datetime import datetime
from bot.services.slack import headers_slack

tp_cfg = config.TP
slack_cfg = config.SLACK


def targetprocess(resource, data={}, include='[Id]', method='get'):
    headers = {
        'Content-Type': 'application/json;charset=UTF-8',
    }
    params = {
        'access_token': tp_cfg['access_token'],
        'format': 'json',
        'include': include
    }
    return requests.__getattribute__(method)(tp_cfg['url'] + '/' + tp_cfg['api_uri'] + '/' + resource, headers=headers, params=params, json=data).json()

def decode_slack_message(text):
    slack_code = {
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '<#[A-Z\\d]+\\|(?P<channel>[^\\sA-Z.]+)>': '#\\g<channel>',
        '<!subteam\^[A-Z\\d]+\\|(?P<subteam>@[A-Za-z\\d]+)>': '\\g<subteam>',
        '<(?P<link>https?://[^\\s|]+)(\\|[^\\s]+)?>': '\\g<link>'
    }
    for encoded, decoded in slack_code.items():
        text = re.sub(encoded, decoded, text)
    for find in re.finditer("<@(?P<user>(U|G)[A-Z\\d]+)>", text):
        user_name = requests.get(slack_cfg['api_url'] + '/users.info',
                                         params={'user': find.group('user')},
                                         headers=headers_slack).json()['user']['profile']['real_name_normalized']
        text = re.sub(find.group(), user_name, text)
    return text


class User_Story:
    states = {}
    for state_name in tp_cfg['story_attributes']['State']:
        states[state_name] = targetprocess('EntityStates',
            {'where': "(Name eq '{0}')and(Process.Name eq '{1}')and(EntityType.Name eq 'UserStory')".format(state_name, tp_cfg['process'])})['Items'][0]['Id']

    priorities = {}
    for priority in tp_cfg['story_attributes']['Priority']:
        priorities[priority] = targetprocess('Priorities',
            {'where': "(Name eq '{0}')and(EntityType.Name eq 'UserStory')".format(priority)})['Items'][0]['Id']

    dev_role_id = targetprocess('Roles', {'where': "(Name eq 'Developer')"})['Items'][0]['Id']
    project_id = targetprocess('Projects', {'where': "Name eq '{0}'".format(tp_cfg['project'])})['Items'][0]['Id']
    team_id = targetprocess('Teams', {'where': "Name eq '{0}'".format(tp_cfg['team'])})['Items'][0]['Id']

    iteration_states = []
    for istate in targetprocess('EntityStates',
                    {'where': "(Process.Name eq '{0}')and(EntityType.Name eq 'UserStory')and(NumericPriority gte {1})".format(
                        tp_cfg['process'],
                        targetprocess('EntityStates',
                            {'where': "(Process.Name eq '{0}')and(EntityType.Name eq 'UserStory')and(IsPlanned eq 'true')".format(tp_cfg['process'])},
                            '[NumericPriority]')['Items'][0]['NumericPriority'])},
                    '[Name]')['Items']:
        iteration_states.append(istate['Name'])

    def __init__(self, current_conversation):
        self.body = {}
        owner_name = requests.get(slack_cfg['api_url'] + '/users.info',
                                  params={'user': current_conversation['Owner']},
                                  headers=headers_slack).json()['user']['profile']['display_name_normalized']
        try:
            self.body.update({
                'Project': {
                  'Id': self.project_id
                },
                'Team': {
                  'Id': self.team_id
                },
                'EntityState': {
                    'Id': self.states[current_conversation.get('State', tp_cfg['default_attributes']['State'])]
                },
                'Priority': {
                    'Id': self.priorities[current_conversation.get('Priority', tp_cfg['default_attributes']['Priority'])]
                },
                'Owner': {
                    'Id': targetprocess('Users',
                        {'where': "Email eq '{0}@{1}'".format(owner_name, tp_cfg['domain'])})['Items'][0]['Id']
                },
                'Name': re.sub('(^|\\s)' + slack_cfg['bot_name'] + '\\s?', '', decode_slack_message(re.sub('\\n', ' ', current_conversation['Name']))),
                'Description': '<!--markdown--> **' + current_conversation['Requester'] + ':**\n' + decode_slack_message(current_conversation['Description']),
                'Tags': slack_cfg['bot_name'],
                'CustomFields': [
                  {
                    'Name': 'Slack Thread',
                    'Value': {
                      'Label': 'Click',
                      'Url': slack_cfg['url'] + '/archives/' + current_conversation['channel'] + '/p' + re.sub('\\.', '', current_conversation['ts'])
                    }
                  }
                ]
            })
            if self.body['Name'] == '':
                self.body['Name'] = "[Bot] {0} Created from {1} request".format(datetime.today().strftime('%d.%m.%Y'), owner_name)
            if current_conversation.get('State', tp_cfg['default_attributes']['State']) in self.iteration_states:
                self.body.update({
                    'TeamIteration': {
                        'Id': targetprocess('TeamIterations',
                            {'where': "(IsCurrent eq 'true')and(Team.Name eq '{0}')".format(tp_cfg['team'])})['Items'][0]['Id']
                    }
                })
        except KeyError:
            return response.json({'ok': 'false', 'status': 'error', 'error': 'Bad request'},
                                headers={'X-Slack-No-Retry': 1},
                                status=400)
        try:
            self.body.update({'PlannedEndDate': current_conversation.get('Deadline')})
        except KeyError:
            pass
        try:
            self.body.update({
              'Assignments': {
                'Items': [
                  {
                    'GeneralUser': {
                      'Id': targetprocess('Users',
                        {'where': "Email eq '{0}@{1}'".format(current_conversation.get('Developer'), tp_cfg['domain'])})['Items'][0]['Id']
                    },
                    'Role': {
                      'Id': self.dev_role_id
                    }
                  }
                ]
              }
            })
        except (IndexError, KeyError):
            pass
