import logging

import yaml

import zendesk, messaging

class TalkCore(object):
    """
    Core class which manages all operations.
    """
    def __init__(
        self,
        slack_bot_token,
        email_domain,
        zendesk_url,
        zendesk_email,
        zendesk_api,
        workflow,
    ):
        # workflow yaml dict
        self.workflow = workflow
        self.slack_worker = messaging.SlackWorker(slack_bot_token, email_domain, workflow)
        self.zen_worker = zendesk.ZenWorker(zendesk_url, zendesk_email, zendesk_api,
                                            workflow['search'])

    def message_actions(self, json_data):
        """
        Performs actions on incoming interactions, i.e. Slack Interactive Components
        """
        update_ticket = self.slack_worker.generate_response(json_data)
        if update_ticket:
            self.zen_worker.update_ticket(*update_ticket)

    def run(self):
        """Runs necessary recurring functions"""
        tickets = self.zen_worker.run()
        self.slack_worker.process_tickets(tickets)
