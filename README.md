# Talktome
Slack chat bot with Zendesk integration

## Prepare

* clone the repo
* prepare a python environment and install deps from requirements.txt
* make sure SLACK_SIGNING_SECRET, SLACK_BOT_TOKEN & SLACK_VERIFICATION_TOKEN are exported to env vars
* start with `gunicorn -b 127.0.0.1:3000 talktome:app`
* start ngrok with `ngrok http 3000`
