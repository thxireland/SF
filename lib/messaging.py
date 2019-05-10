#/usr/bin/env python
import datetime
import logging
import random
import time

from slackclient import SlackClient

NUDGE_TEXT = ['hello?', 'any news?', 'could you please click one of the buttons?',
              'still there?']


class SlackWorker(object):
    """
    Iterates over tickets, creates/opens conversations
    """
    def __init__(self, bot_token, domain, workflow):
        self.client = SlackClient(bot_token)
        self.domain = domain
        info = self.client.api_call("auth.test")
        self.bot_id = info['user_id']
        self.workflow = workflow

    def process_tickets(self, tickets):
        """
        Iterate over tickets and engage with users
        """
        for ticket_id, ticket_data in tickets.items():
            slack_user = self.get_slack_user(ticket_data.username)
            # check if there was a conversation with the user regarding this ticket
            conversation = self.client.api_call("conversations.open", users=[slack_user])
            channel_id = conversation['channel']['id']
            some_time_ago = datetime.datetime.now() - datetime.timedelta(hours=3)
            timestamp = time.mktime(some_time_ago.timetuple())
            history = self.client.api_call("conversations.history", channel=channel_id,
                                           oldest=timestamp)
            # search for a last message sent by bot
            last_message = {}
            for message in history['messages']:
                # TODO: find a way to check bot_id
                if 'bot_id' in message and 'blocks' in message and (
                        any([True for b in message['blocks']
                             if b['block_id'] == self.workflow['label']])):
                    last_message = message
                    break
            # first time message
            if not last_message:
                text = self.workflow['message'].format(barcode=ticket_data.barcode)
                choices = self.workflow['choices']
                blocks = self.build_blocks(text, choices, ticket_id)
                logging.debug(blocks)
                self.send_block_message(channel_id, blocks)
            # nudge a user if last message is an unanswered question
            # TODO: needs work
            #if last_message:
            #    history = self.client.api_call("conversations.history", channel=channel_id,
            #                                   oldest=timestamp)
            #    if (not history['messages'][0]['text'] in NUDGE_TEXT and
            #        any(['blocks' in message
            #           for message in history['messages'][:len(NUDGE_TEXT)]])):
            #        self.send_text_message(channel_id, random.choice(NUDGE_TEXT))


    def generate_response(self, json_data):
        """
        Generates a response for an action performed by a user, e.g. button click.
        Returns a dict with ticket id and a message if a ticket needs to ne updated.
        """
        # delete all actions
        logging.debug("incoming %s", json_data)
        no_button_blocks = [
            block for block in json_data['message']['blocks'] if block['type'] != "actions"]
        actions = json_data['actions'][0]
        ticket_id = actions['value']
        action_id = actions['action_id']
        channel_id = json_data['container']['channel_id']
        message_ts = json_data['container']['message_ts']
        self.client.api_call("chat.update", channel=channel_id, ts=message_ts,
                             blocks=no_button_blocks)
        reply_text = "You answered: _{}_".format(actions['text']['text'])
        self.send_text_message(channel_id, reply_text)
        current_step = self.recurse_workflow(self.workflow, action_id)
        update_ticket = ()
        if "choices" in current_step:
            blocks = self.build_blocks(current_step['message'], current_step['choices'],
                                                   ticket_id)
            self.send_block_message(channel_id, blocks)
        elif "update_ticket" in current_step:
            update_ticket = (ticket_id, current_step["update_ticket"])
            self.send_text_message(channel_id, current_step['message'])
        return update_ticket

    def recurse_workflow(self, step, key):
        """
        Recurses and returns requested workflow step
        """
        if not isinstance(step, dict):
            return step
        if "choices" in step.keys():
            if key in step["choices"].keys():
                return step["choices"][key]
            else:
                for choice in step["choices"].keys():
                    result = self.recurse_workflow(step["choices"][choice], key)
                    if result:
                        return result

    def create_button(self, label, action, ticket_id):
        """
        Generates necessary structure for a button.
        """
        return {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": label,
            },
            "value": str(ticket_id),
            "action_id": str(action)
        }

    def build_blocks(self, text, choices, ticket_id):
        return [
            {
                "type": "section",
                "text": {
                    "type": "plain_text",
                    "text": text,
                },
                "block_id": self.workflow['label']  # this is a key to determine a workflow
            },
            {
                "type": "actions",
                "elements": [self.create_button(data['label'], action, ticket_id)
                             for action, data in choices.items()]
            },
        ]

    def get_slack_user(self, username):
        """
        Returns slack user id based on username
        """
        return self.client.api_call("users.lookupByEmail",
            email="{}@{}".format(username, self.domain))['user']['id']

    def send_text_message(self, channel_id, text):
        """
        Sends a basic text message to a given channel.
        """
        self.client.api_call("chat.postMessage", channel=channel_id, as_user="false", text=text)

    def send_block_message(self, channel_id, blocks):
        """
        Sends given list of blocks to a channel with id.
        """
        self.client.api_call("chat.postMessage", channel=channel_id, as_user="false",
                             blocks=blocks)
