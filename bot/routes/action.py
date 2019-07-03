from sanic import response
from sanic.response import json
from sanic.log import logger
import config
import json
import requests

from bot.services.slack import headers_slack
from bot.services.tp import targetprocess, User_Story

from bot import app, bp

slack_cfg = config.SLACK
tp_cfg = config.TP


@bp.route('/action', methods=['POST'])
async def action(request):
    try:
        # Get action and conversation ts
        recieved_action = json.loads(request.form['payload'][0])['actions'][0]
        conversation_ts = recieved_action['action_id'].split('_')[-1]

        # Fill current conversation user story attributes
        if recieved_action['type'] != 'button':
            if recieved_action['type'] == 'static_select':
                app.sessions_dict[conversation_ts][recieved_action['placeholder']['text']] = \
                    recieved_action['selected_option']['value']
            elif recieved_action['type'] == 'datepicker':
                app.sessions_dict[conversation_ts]['Deadline'] = recieved_action['selected_date']
        else:
            # Create User Story and post link to slack
            if recieved_action['value'] == 'create':
                # Get parent request message text
                params = {
                    'channel': app.sessions_dict[conversation_ts]['channel'],
                    'latest': conversation_ts,
                    'inclusive': 'true',
                    'limit': 1
                }
                parent_message = requests.get(slack_cfg['api_url'] + '/conversations.history', headers=headers_slack, params=params).json()['messages'][0]

                app.sessions_dict[conversation_ts]['Description'] = parent_message['text']
                if 'user' in parent_message:
                    app.sessions_dict[conversation_ts]['Requester'] = requests.get(slack_cfg['api_url'] + '/users.info',
                                                                                   params={'user': parent_message['user']},
                                                                                   headers=headers_slack).json()['user']['profile']['display_name_normalized']
                elif 'username' in parent_message:
                    app.sessions_dict[conversation_ts]['Requester'] = parent_message['username']
                else:
                    app.sessions_dict[conversation_ts]['Requester'] = ''

                if 'attachments' in parent_message:
                    for attachment in parent_message["attachments"]:
                        for field in slack_cfg['attachments_fields']:
                            if field in attachment:
                                app.sessions_dict[conversation_ts]['Description'] += '\n' + str(attachment[field])

                if 'files' in parent_message:
                    for file in parent_message["files"]:
                        app.sessions_dict[conversation_ts]['Description'] += '\n' + '[' + file['title'] + '](' + file['url_private'] + ')'

                user_story = User_Story(app.sessions_dict[conversation_ts])
                logger.info("user_story instance {0}".format(json.dumps(user_story.body, indent=4, sort_keys=True)))
                user_story_id = targetprocess(resource='UserStories', data=user_story.body, method='post')['Id']
                json_data = {
                    'channel': app.sessions_dict[conversation_ts]['channel'],
                    'thread_ts': conversation_ts,
                    'text': "Link: {0}/entity/{1}".format(tp_cfg['url'], user_story_id)
                }
                requests.post(slack_cfg['api_url'] + '/chat.postMessage', headers=headers_slack, json=json_data)

            # Cleanup after canceled or created user story
            response_url = json.loads(request.form['payload'][0])['response_url']
            requests.post(response_url, headers=headers_slack, json={'delete_original': True})
            del app.sessions_dict[conversation_ts]

        return response.json({'ok': 'true', 'status': 'Action recieved'}, status=200)
    except Exception as e:
        logger.error(e)
        return response.json({'ok': 'false', 'status': 'error', 'error': 'Bad request'},
                             headers={'X-Slack-No-Retry': 1},
                             status=400)
