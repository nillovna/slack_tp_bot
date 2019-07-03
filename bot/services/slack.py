import config
import requests
import copy
from datetime import datetime

slack_cfg = config.SLACK
tp_cfg = config.TP

headers_slack = {
    'Content-Type': 'application/json;charset=UTF-8',
    'Authorization': 'Bearer ' + slack_cfg['token']
}

usergroups = requests.get(slack_cfg['api_url'] + '/usergroups.list',
                          headers=headers_slack).json()['usergroups']
usergroup_id = [usergroup['id'] for usergroup in usergroups if usergroup['handle'] == slack_cfg['group']][0]
users_ids = requests.get(slack_cfg['api_url'] + '/usergroups.users.list',
                         params={'usergroup': usergroup_id},
                         headers=headers_slack).json()['users']

developer_users = []
if not tp_cfg["story_attributes"]["Developer"]:
    for user_id in users_ids:
        developer_users.append(
            requests.get(slack_cfg['api_url'] + '/users.info',
                         params={'user': user_id},
                         headers=headers_slack).json()['user']['profile']['display_name_normalized'])


class Slack_Dialog:
    heading = {
        'type': 'section',
        'text': {
            'type': 'mrkdwn',
            'text': 'What UserStory would you like to create?'
        }
    }

    def __init__(self, ts, users):

        self.story_attributes = copy.deepcopy(tp_cfg['story_attributes'])

        if not self.story_attributes['Developer']:
            self.story_attributes['Developer'] = users

        self.select = {
            'type': 'actions',
            'elements': []
        }
        for key, values in sorted(self.story_attributes.items()):
            element = {
                'type': 'static_select',
                'action_id': key + '_' + ts,
                'placeholder': {
                    'type': 'plain_text',
                    'text': key
                },
                'options': []
            }
            for value in values:
                element['options'].append(
                    {
                        'text': {
                            'type': 'plain_text',
                            'text': value
                        },
                        'value': value
                    }
                )
            self.select['elements'].append(element)
        self.datepicker = {
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': 'Deadline'
            },
            'accessory': {
                'type': 'datepicker',
                'initial_date': datetime.today().strftime('%Y-%m-%d'),
                'action_id': 'deadline_' + ts,
                'placeholder': {
                    'type': 'plain_text',
                    'text': 'Select a date'
                }
            }
        }
        self.buttons = {
            'type': 'actions',
            'elements': [
                {
                    'type': 'button',
                    'text': {
                        'type': 'plain_text',
                        'text': 'Create UserStory'
                    },
                    'action_id': 'create_' + ts,
                    'style': 'primary',
                    'value': 'create'
                },
                {
                    'type': 'button',
                    'text': {
                        'type': 'plain_text',
                        'text': 'Cancel'
                    },
                    'action_id': 'cancel_' + ts,
                    'value': 'cancel'
                }
            ]
        }
