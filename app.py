#starting code from https://github.com/slackapi/python-slack-sdk/tree/main/tutorial
import logging
from slack_bolt import App
from slack_sdk.web import WebClient
import bot_messages

# Initialize a Bolt for Python app
app = App()

# For simplicity we'll store our app data in-memory with the following data structure.
# onboarding_tutorials_sent = {"channel": {"user_id": OnboardingTutorial}}
onboarding_tutorials_sent = {}


def start_onboarding(user_id: str, channel: str, client: WebClient):
    # Create a new onboarding tutorial.
    tutorial = bot_messages.OnboardingTutorial(channel)

    # Get the onboarding message payload
    message = tutorial.get_message_payload()

    # Post the onboarding message in Slack
    response = client.chat_postMessage(**message)

    # Capture the timestamp of the message we've just posted so
    # we can use it to update the message after a user
    # has completed an onboarding task.
    tutorial.timestamp = response["ts"]

    # Store the message sent in onboarding_tutorials_sent
    if channel not in onboarding_tutorials_sent:
        onboarding_tutorials_sent[channel] = {}
    onboarding_tutorials_sent[channel][user_id] = tutorial


# ================ Team Join Event =============== #
# When the user first joins a team, the type of the event will be 'team_join'.
# Here we'll link the onboarding_message callback to the 'team_join' event.

# Note: Bolt provides a WebClient instance as an argument to the listener function
# we've defined here, which we then use to access Slack Web API methods like conversations_open.
# For more info, check out: https://slack.dev/bolt-python/concepts#message-listening
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
# When a users adds an emoji reaction to the message, the type of the event will be 'reaction_added'.
@app.event("reaction_added")
def update_emoji(event, client):
    # Get the ids of the Slack channel, reaction, and timestamp of message reacted to associated with the incoming event
    channel_id = event.get("item", {}).get("channel")
    reaction = event.get("reaction")
    message_ts = event.get("item", {}).get("ts")

    # bot begins asking questions if the reaction is a round pushpin and then if the message has not been scraped already.
    # if the message has been scraped, post a message reminding the user.
    if reaction == "round_pushpin":
        if not message_in_documentation(message_ts):
            client.chat_postMessage(channel=channel_id, text=bot_messages.question_one, thread_ts=message_ts)
        else:
            client.chat_postMessage(channel=channel_id, text=bot_messages.already_scraped, thread_ts=message_ts)


# ============== Message Events ============= #
# When a user sends a message to a channel, the event type will be 'message'.
@app.event("message")
def message(event, client):
    channel_id = event.get("channel")
    user_id = event.get("user")
    text = event.get("text")
    message_ts = event.get("ts")
    message_thread_ts = event.get("thread_ts")

    # sends the onboarding message if "start" is typed.
    try:
        if text.lower() == "start":
            return start_onboarding(user_id, channel_id, client)
    # AttributeError occurs when text doesn't have a .lower() attribute.
    # AttributeError occurs when ONLY links are sent to the channel.
    # Ex. A user typing "https://www.slack.com" will cause AttributeError.
    # This error is of minimal impact to the entirety of the code. No error logging is necessary.
    except AttributeError:
        logger.info("AttributeError has occurred due to a posted message being solely a link.")

    # Scrapes message into the terminal; used for debugging purposes.
    logger.info(f"New Message: {text}")

    # The code below asks supplemental questions (except the title) and records user replies.
    # ========================= Code Start ========================= #

    # if the message is in a thread, proceed; if not, ignore.
    if message_thread_ts != None:
        # has_round_pushpin checks whether the parent message of the thread has a round pushpin reaction and returns a boolean.
        # the variable uses the reactions.get method, which retrieves more than just the names of the reactions on the message. 
        # for more information: https://api.slack.com/methods/reactions.get 
        has_round_pushpin = "round_pushpin" in str(client.reactions_get(channel=channel_id, timestamp=message_thread_ts).get("message", {}).get("reactions", {}))

        # if the parent message has a round pushpin reaction, proceed; if not, ignore.
        if has_round_pushpin:
            # if the parent message has not been documented, proceed; if not, ignore.
            if not message_in_documentation(message_thread_ts):
                # creates a temporary variable to record number of the last question that was asked.
                last_question_asked = 0

                # Calls conversations.replies to get the thread history AND the message intended to be scraped.
                # for more information on the conversation.replies method: https://api.slack.com/methods/conversations.replies
                thread_message_history = client.conversations_replies(
                    channel=channel_id,
                    inclusive=True,
                    ts=message_thread_ts,
                    latest=message_ts
                )["messages"]

                # compares the thread message history to the individual questions. 
                # if a the exact string of a question is in message["text"], change the value of last_question_asked accordingly.
                for message in thread_message_history:
                    if message["text"] == bot_messages.question_one:
                        last_question_asked = 1
                    elif message["text"] == bot_messages.question_two:
                        last_question_asked = 2
                    elif message["text"] == bot_messages.question_three:
                        last_question_asked = 3

                # bot records response to question 1 and asks question 2 afterwards.
                if last_question_asked == 1:
                    client.chat_postMessage(channel=channel_id, text=bot_messages.response_recorded, thread_ts=message_thread_ts)
                    client.chat_postMessage(channel=channel_id, text=bot_messages.question_two, thread_ts=message_ts)
                    file_write(f"# {text}\n")
                # bot records response to question 2 and asks question 3 afterwards.
                elif last_question_asked == 2:
                    client.chat_postMessage(channel=channel_id, text=bot_messages.response_recorded, thread_ts=message_thread_ts)
                    client.chat_postMessage(channel=channel_id, text=bot_messages.question_three, thread_ts=message_ts)

                    if text == "None":
                        file_write("No supplemental image was provided.\n\n")
                    else:
                        # Note: only links of images will work. uploading an image file will not be recognized.
                        file_write(f"![Supplemental Image]({text})\n\n")
                # bot records response to question 3.
                # bot also records the originally scraped message and the timestamp of that scraped message.
                # the timestamp is used to check whether that message has been scraped already. it is used in the function message_in_documentation().
                elif last_question_asked == 3:
                    client.chat_postMessage(channel=channel_id, text=bot_messages.response_recorded, thread_ts=message_thread_ts)
                    client.chat_postMessage(channel=channel_id, text=bot_messages.wiki_page_made, thread_ts=message_ts)
                    scraped_message = thread_message_history[0]["text"]
                    if text == "None":
                        file_write(f"## Original Documentation:\n\n{scraped_message}\n\n## Additional Info:\n\n###### Message Timestamp: {message_thread_ts}\n\n")
                    else:
                        file_write(f"## Original Documentation:\n\n{scraped_message}\n\n## Additional Info:\n\n{text}\n\n###### Message Timestamp: {message_thread_ts}\n\n")

    # ========================= Code End ========================= #


# a function that uses the timestamp of a message to check if that timestamp exists in the markdown file already.
# in other words, this will check whether a message has already been scraped.
def message_in_documentation(message_ts: str):
    with open("PythOnBoardingBot/messages.md", "a+") as file:
        file.seek(0)
        return message_ts in file.read()

# a function to write desired text into the markdown file.
def file_write(text):
    with open("PythOnBoardingBot/messages.md", "a+") as file:
        return file.write(text)


if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())
    app.start(3000)