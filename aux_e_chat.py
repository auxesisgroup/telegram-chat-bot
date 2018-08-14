import time
import telepot
import ConfigParser
import logging

from telepot.loop import MessageLoop
from telepot.delegate import (
    create_open, pave_event_space,
    include_callback_query_chat_id, per_chat_id)

from db_folder import db_config


db_client_connection = db_config.mongo_connection()
db_name = db_client_connection['auxesis_chatbot_db']
db_updates_collection = db_name['new_users_table']

config = ConfigParser.ConfigParser()
config.read('config.ini')

TOKEN = config.get('General', 'api_key')
administrators = list(map(int, config.get('General', 'admins').split(',')))


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename='log.log', level=logging.INFO)


class AuxEChat(telepot.helper.ChatHandler):
    def __init__(self, *args, **kwargs):
        super(AuxEChat, self).__init__(*args, **kwargs)

    def on_chat_message(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
        if content_type == "new_chat_member":
            user_name = '@{}'.format(msg['new_chat_participant']['first_name'])
            if len(user_name) > 3:
                if msg['new_chat_participant']['is_bot'] is True & msg['new_chat_participant']['id'] not in administrators:
                    self.bot.kickChatMember(msg['chat']['id'], msg['new_chat_participant']['id'])
                    logging.info("User %s (ID: %s) Kicked Out of the Group! Hooray!", user_name, msg['new_chat_participant']['id'])
                else:
                    new_user_name = msg['new_chat_participant']['first_name']
                    new_user = new_user_name.title()
                    db_updates_collection.insert_one(
                        {
                            'new_user': new_user,
                            'chat_id': msg['chat']['id'],
                            'message_id': msg['message_id'],
                            'date': msg['date']
                        }
                    )
                    self._sent_message()
                    logging.info("{} has joined with {} chat id to {} group .", user_name, msg['chat']['id'], msg['chat']['title'])

            else:
                self.bot.kickChatMember(msg['chat']['id'], msg['new_chat_participant']['id'])
                logging.info("User %s (ID: %s) Kicked Out of the Group! Hooray!", user_name, msg['new_chat_participant']['id'])

        if content_type == "text":
            if msg['text'].lower().startswith(("wh", "how")) or msg['text'].lower().endswith(("?")):
                self.sender.sendMessage(text= "Thanks for asking Question with us !! You can find relative answer here in [whitepaper](https://auxledger.org/) Till our admin team review your question.",
                    parse_mode='Markdown')

    def _sent_message(self):
        while True:
            new_users_list = list(db_updates_collection.find({}, {"date": 1, "new_user": 1, "_id": 0}))
            last_date_range = int(db_updates_collection.find_one(sort=[("date", -1)])["date"])
            date_range = last_date_range - 30
            date_s = [d for d in range(date_range, last_date_range)]

            users_list = [d["new_user"] for d in new_users_list if d["date"] in date_s]

            if len(users_list) >= 2:
                self.sender.sendMessage(
                    text="Hey, *" + ','.join(users_list) + "* ! Welcome to Auxledger community.Did you checked our [website](https://auxledger.org/) and got yourself whitelisted? Do check out pinned message for regular updates and engage in our growing community.",
                    parse_mode='Markdown')
                users_list *= 0
            else:
                new_last_user = db_updates_collection.find_one(sort=[("date", -1)])["new_user"]
                self.sender.sendMessage(
                    text="Hey, *{}* ! Welcome to Auxledger community.Did you checked our [website](https://auxledger.org/) and got yourself whitelisted? Do check out pinned message for regular updates and engage in our growing community.".format(
                        new_last_user),
                    parse_mode='Markdown')


bot = telepot.DelegatorBot(TOKEN, [
    include_callback_query_chat_id(
        pave_event_space())(
            per_chat_id(types=['group']), create_open, AuxEChat, timeout=200),
])


def main():
    MessageLoop(bot).run_as_thread()
    logging.info("Bot started.")

    while 1:
        time.sleep(15)


if __name__ == '__main__':
    main()
