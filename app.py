#starting code from https://github.com/slackapi/python-slack-sdk/tree/main/tutorial
import logging
import os
from slack_bolt import App
from slack_sdk.web import WebClient
from onboarding_tutorial import OnboardingTutorial
from slack_sdk.errors import SlackApiError

# Initialize a Bolt for Python app
app = App()

# For simplicity we'll store our app data in-memory with the following data structure.
# onboarding_tutorials_sent = {"channel": {"user_id": OnboardingTutorial}}
onboarding_tutorials_sent = {}


def start_onboarding(user_id: str, channel: str, client: WebClient):
    # Create a new onboarding tutorial.
    onboarding_tutorial = OnboardingTutorial(channel)

    # Get the onboarding message payload
    message = onboarding_tutorial.get_message_payload()

    # Post the onboarding message in Slack
    response = client.chat_postMessage(**message)

    # Capture the timestamp of the message we've just posted so
    # we can use it to update the message after a user
    # has completed an onboarding task.
    onboarding_tutorial.timestamp = response["ts"]

    # Store the message sent in onboarding_tutorials_sent
    if channel not in onboarding_tutorials_sent:
        onboarding_tutorials_sent[channel] = {}
    onboarding_tutorials_sent[channel][user_id] = onboarding_tutorial


# ================ Team Join Event =============== #
# When the user first joins a team, the type of the event will be 'team_join'.
# Here we'll link the onboarding_message callback to the 'team_join' event.

# Note: Bolt provides a WebClient instance as an argument to the listener function
# we've defined here, which we then use to access Slack Web API methods like conversations_open.
# For more info, checkout: https://slack.dev/bolt-python/concepts#message-listening
@app.event("team_join")
def onboarding_message(event, client):
    """Create and send an onboarding welcome message to new users. Save the
    time stamp of this message so we can update this message in the future.
    """
    # Get the id of the Slack user associated with the incoming event
    user_id = event.get("user", {}).get("id")

    # Open a DM with the new user.
    response = client.conversations_open(users=user_id)
    channel = response["channel"]["id"]

    # Post the onboarding message.
    start_onboarding(user_id, channel, client)


# ============= Reaction Added Events ============= #
# When a users adds an emoji reaction to the onboarding message,
# the type of the event will be 'reaction_added'.
# Here we'll link the update_emoji callback to the 'reaction_added' event.
@app.event("reaction_added")
def update_emoji(event, client):
    """Update the onboarding welcome message after receiving a "reaction_added"
    event from Slack. Update timestamp for welcome message as well.
    """
    # Get the ids of the Slack user, channel, reaction, and timestamp of message reacted to associated with the incoming event
    channel_id = event.get("item", {}).get("channel")
    user_id = event.get("user")
    reaction = event.get("reaction")
    message_ts = event.get("item", {}).get("ts")
    message_thread_ts = event.get("item", {}).get("thread_ts")

    # reactions and message only logged if the reaction is a round pushpin
    if reaction == "round_pushpin":
        # initializes the file for the messages
        file = open("PythOnBoardingBot/messages.txt", "a+")

        try:
            # Call the conversations.history method using the WebClient
            # The client passes the token you included in initialization    
            result = client.conversations_history(
                channel=channel_id,
                inclusive=True,
                oldest=message_ts,
                latest=message_ts,
                limit=1
            )
            message = result["messages"][0]

            # Print message text
            logger.info("{} has reacted with a '{}' to {}".format(user_id, reaction, message["text"]))
            client.chat_postMessage(channel=channel_id, text="What do you want to title this wiki?", thread_ts=message_ts)

            #  writes the message that was being reacted to into the messages.txt file
            file.write("{}\n".format(message["text"]))
            file.close()

        except SlackApiError as e:
            logger.info(f"Error: {e}")



# =============== Pin Added Events ================ #
# When a users pins a message the type of the event will be 'pin_added'.
# Here we'll link the update_pin callback to the 'pin_added' event.
@app.event("pin_added")
def update_pin(event, client):
    """Update the onboarding welcome message after receiving a "pin_added"
    event from Slack. Update timestamp for welcome message as well.
    """
    # Get the ids of the Slack user and channel associated with the incoming event
    channel_id = event.get("channel_id")
    user_id = event.get("user")

    # Get the original tutorial sent.
    onboarding_tutorial = onboarding_tutorials_sent[channel_id][user_id]

    # Mark the pin task as completed.
    onboarding_tutorial.pin_task_completed = True

    # Get the new message payload
    message = onboarding_tutorial.get_message_payload()

    # Post the updated message in Slack
    updated_message = client.chat_update(**message)


# ============== Message Events ============= #
# When a user sends a message to a channel, the event type will be 'message'.
# Here we'll link the message callback to the 'message' event.
@app.event("message")
def message(event, client):
    channel_id = event.get("channel")
    user_id = event.get("user")
    text = event.get("text")
    message_ts = event.get("ts")
    message_thread_ts = event.get("thread_ts")

    # logs the message in the terminal, but NOT write it to a text file.
    if text and text.lower() == "start":
        return start_onboarding(user_id, channel_id, client)

    logger.info("{} sent message: {}".format(user_id, text))

    # if the message is sent as a threaded reply within ten minutes of the original message, 
    # it'll be written into messages.txt as the title of documentation. Will fix later.
    try:    
        print(float(message_ts) - float(message_thread_ts))
        if float(message_ts) - float(message_thread_ts) <= 600:
            client.chat_postMessage(channel=channel_id, text="Got it.", thread_ts=message_thread_ts)
            # initializes the file for the messages and puts cursor at the last line
            file = open("messages.txt", "a+")
            file.write("Title of Documentation: {}\n".format(text))
            file.close()
    except TypeError:
        return


if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())
    app.start(3000)
