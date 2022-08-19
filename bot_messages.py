# This file contains all of the messages that the Slack Bot sends in channels.
# slackbot tutorial original code from https://github.com/slackapi/python-slack-sdk/tree/main/tutorial, modified.

# questions that the bot asks when documenting
question_one = "What do you want to title this wiki?"
question_two = "Do you want to upload a supplemental image? If so, upload a link of the image. If not, type \"None\"."
question_three = "Do you want to add anything else? If so, type any supplemental information you wish to add. If not, type \"None\"."
already_scraped = "This message has already been turned into a wiki page!"
response_recorded = "Response recorded."
wiki_page_made = "The wiki page has been created."

class OnboardingTutorial:
    """Constructs the onboarding message and stores the state of which tasks were completed."""

    WELCOME_BLOCK = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": (
                "Welcome to Slack! :wave: We're so glad you're here. :blush:\n\n\n"
                "*Who am I?*\n\n"
            ),
        },
    }

    ABOUT_ME_BLOCK = {
    "type": "section",
    "text": {
        "type": "mrkdwn",
        "text": (
            "I am a bot that allows you to react to the messages to add it to a documentation! Never lose your documentation in Slack channels ever again!\n\n\n"
            "*How can I be activated?*"
        ),
    },
}
    DIVIDER_BLOCK = {"type": "divider"}

    END_BLOCK = {
    "type": "section",
    "text": {
        "type": "mrkdwn",
        "text": (
            "After you have prompted me to save a message, I will only save it *after you answer a few supplemental questions*:\n\n"
            f"1. {question_one}\n"
            f"2. {question_two}\n"
            f"3. {question_three}"
        ),
    },
}

    def __init__(self, channel):
        self.channel = channel
        self.username = "pythonboardingbot"
        self.icon_emoji = ":robot_face:"
        self.timestamp = ""
        self.reaction_task_completed = False
        self.pin_task_completed = False

    def get_message_payload(self):
        return {
            "ts": self.timestamp,
            "channel": self.channel,
            "username": self.username,
            "icon_emoji": self.icon_emoji,
            "blocks": [
                self.WELCOME_BLOCK,
                self.DIVIDER_BLOCK,
                self.ABOUT_ME_BLOCK,
                self.DIVIDER_BLOCK,
                *self._get_reaction_block(),
                *self._get_pin_block(),
                self.DIVIDER_BLOCK,
                self.END_BLOCK
            ],
        }

    def _get_reaction_block(self):
        text = (
            "*Add an emoji reaction to this message* :round_pushpin:\n"
            "You can quickly respond to any message on Slack with an emoji reaction. "
            "React with a :round_pushpin: to prompt me to save the message to a wiki page."
        )
        information = (
            ":information_source: *<https://get.slack.help/hc/en-us/articles/206870317-Emoji-reactions|"
            "How to Use Emoji Reactions>*"
        )
        return self._get_task_block(text, information)

    def _get_pin_block(self):
        text = (
            "*Pin this message* :pushpin:\n"
            "Important messages and files can be pinned to the details pane in any channel or"
            " direct message, including group messages, for easy reference. "
            "Pinning any message also prompts me to save the message to a wiki page."
        )
        information = (
            ":information_source: *<https://get.slack.help/hc/en-us/articles/205239997-Pinning-messages-and-files"
            "|How to Pin a Message>*"
        )
        return self._get_task_block(text, information)

    @staticmethod
    def _get_checkmark(task_completed: bool) -> str:
        if task_completed:
            return ":white_check_mark:"
        return ":white_large_square:"

    @staticmethod
    def _get_task_block(text, information):
        return [
            {"type": "section", "text": {"type": "mrkdwn", "text": text}},
            {"type": "context", "elements": [{"type": "mrkdwn", "text": information}]},
        ]
