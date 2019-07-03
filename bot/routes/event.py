from sanic import response
from sanic.response import json
from sanic.log import logger
import re
import requests
import config
import json

from bot.services.slack import Slack_Dialog, usergroup_id, users_ids, developer_users, headers_slack

from bot import app, bp

slack_cfg = config.SLACK
tp_cfg = config.TP


@bp.route('/event', methods=['POST'])
async def event(request):
    try:

        # Slack special verification event
        if request.json['type'] == 'url_verification':
            return response.json({'challenge': request.json['challenge']})

        recieved_event = request.json['event']

        # Event about changed SLACK group membership
        if recieved_event['type'] == 'subteam_members_changed' and recieved_event['subteam_id'] == usergroup_id:
            for subteam_members_delta, delta_action in slack_cfg['map_subteam_members_changed'].items():
                for user_id in recieved_event[subteam_members_delta]:
                    users_ids.__getattribute__(delta_action)(user_id)
                    if not tp_cfg["story_attributes"]["Developer"]:
                        developer_users.__getattribute__(delta_action)(
                                requests.get(slack_cfg['api_url'] + '/users.info',
                                             params={'user': user_id},
                                             headers=headers_slack).json()['user']['profile']['display_name_normalized'])
            logger.info("SLACK group members changed: {0}".format(developer_users))

        # Event to create UserStory
        if recieved_event['type'] == 'app_mention':
            assert ('thread_ts' in recieved_event), 'Wrong event'
            # Prepare request body to post slack message
            json_data = {
                'channel': recieved_event['channel'],
                'user': recieved_event['user'],
                'thread_ts': recieved_event['thread_ts']
            }

            # Verify that user called bot is in SLACK group
            if recieved_event['user'] in users_ids:
                # Check that User Story creation is not already in progress
                if recieved_event['thread_ts'] in app.sessions_dict:
                    assert (recieved_event['event_ts'] != app.sessions_dict[recieved_event['thread_ts']]['event_ts']), 'Duplicated request'
                    json_data['text'] = 'Sorry, UserStory creation already in progress'
                else:
                    logger.info("Recieved event {0}".format(json.dumps(recieved_event, indent=4, sort_keys=True)))
                    # Update sessions_dict
                    app.sessions_dict.update({
                        recieved_event['thread_ts']: {
                            'event_ts': recieved_event['event_ts'],
                            'channel': recieved_event['channel'],
                            'ts': recieved_event['thread_ts'],
                            'Owner': recieved_event['user'],
                            'Name': recieved_event['text']
                        }
                    })
                    logger.info("Recorded to app.sessions_dict {0}".format(json.dumps(app.sessions_dict[recieved_event['thread_ts']], indent=4, sort_keys=True)))
                    # Dialog message
                    dialog_el = Slack_Dialog(recieved_event['thread_ts'], developer_users)
                    json_data['blocks'] = [dialog_el.heading, dialog_el.select, dialog_el.datepicker, dialog_el.buttons]
            else:
                # Permission denied message
                json_data['blocks'] = slack_cfg['permission_denied_block']

            # Post slack message
            requests.post(slack_cfg['api_url'] + '/chat.postEphemeral', headers=headers_slack, json=json_data)

        # Everything fine with event, return 200 to Slack
        return response.json({'ok': 'true', 'status': 'Slack event successfully recieved'}, status=200)

    except Exception as e:
        logger.error(e)
        if str(e) != 'Duplicated request':
            try:
                del app.sessions_dict[recieved_event['thread_ts']]
            except KeyError:
                pass
        return response.json({'ok': 'false', 'status': 'error', 'error': 'Bad request'},
                             headers={'X-Slack-No-Retry': 1},
                             status=400)
