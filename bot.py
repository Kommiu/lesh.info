import logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
import sqlite3 
from functools import partial
from configparser import ConfigParser
from functools import wraps
from telegram import ParseMode
from telegram.utils.helpers import mention_html
import sys
import traceback
import click
from telegram import ChatAction
from telegram.ext import Updater, MessageHandler, Filters

import dialogflow_v2 as df

def send_typing_action(func):
    """Sends typing action while processing func command."""
    @wraps(func)
    def command_func(self, update, context, *args, **kwargs):
        context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)
        return func(self, update, context,  *args, **kwargs)

    return command_func


class Bot():
    def __init__(self, project_id, language_code, tg_token, admins, db_path):
        self.project_id = project_id
        self.language_code = language_code
        self.session_client = df.SessionsClient()
        self.updater = Updater(
            token=tg_token,
            use_context=True,
        )
        self.admins = [int(x) for x in admins.split(' ')]
        self.dispatcher = self.updater.dispatcher
        self.db_path = db_path
        self.processor_map = {
            'who_comes': self._process_whocomes,
            'check_discount': self._process_discount,
        }

    def run(self):
        
        respond_handler = MessageHandler(Filters.text, self._respond)
        self.dispatcher.add_handler(respond_handler)
        self.dispatcher.add_error_handler(self._error_handler)
        self.updater.start_polling()

    def process(self, response, update, context, session):
        processor = self.processor_map.get(
            response.query_result.intent.display_name,
            self._process_default
        )
        processor(response, update, context, session)

    def _process_default(self, response, update, context, session):
        response_lines = response.query_result.fulfillment_text.split('\n')
        for line in response_lines:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=line,
            )
    def _process_discount(self, response, update, context, session):
        fio = response.query_result.parameters['fio']
        year = response.query_result.parameters['birth_year']

        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                '''
                SELECT COUNT(*)
                FROM fees
                WHERE ФИО=:fio
                AND 'год рождения'=:year
                ''',
                {'fio': fio, 'year': year}
            )
            count = c.fetchall()[0][0]
        if count == 0:
            new_response = self.detect_intent('Нет', session)
        else:
            new_response = self.detect_intent('Да', session)

        self.process(new_response, update, context, session)

    def _process_whocomes(self, response, update, context, session):
        name = response.query_result.parameters['teacher_name']
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                '''
                SELECT COUNT(*)
                FROM teachers
                WHERE Фамилия=?
                ''',
                (name, )
            )
            count = c.fetchall()
        if count == 0:
            new_response = self.detect_intent('Нет', session)
        else:
            new_response = self.detect_intent('Да', session)

        self.process(new_response, update, context, session)
    @send_typing_action
    def _respond(
            self,
            update,
            context,
    ):
        if not update.message or not update.message.text:
            return

        session_id = update.effective_user.id
        session = self.session_client.session_path(self.project_id, session_id)
        text = update.message.text
        response = self.detect_intent(text, session)
        self.process(response, update, context, session)
        

    def _error_handler(self, update, context):
        devs = self.admins
        if update.effective_message:
            text = "Hey. I'm sorry to inform you that an error happened while I tried to handle your update. " \
                   "My developer(s) will be notified."
            update.effective_message.reply_text(text)

        trace = "".join(traceback.format_tb(sys.exc_info()[2]))
        payload = ""
        if update.effective_user:
            payload += f' with the user {mention_html(update.effective_user.id, update.effective_user.first_name)}'
        if update.effective_chat:
            payload += f' within the chat <i>{update.effective_chat.title}</i>'
            if update.effective_chat.username:
                payload += f' (@{update.effective_chat.username})'
        if update.poll:
            payload += f' with the poll id {update.poll.id}.'
        text = f"Hey.\n The error <code>{context.error}</code> happened{payload}. The full traceback:\n\n<code>{trace}" \
               f"</code>"
        for dev_id in devs:
            context.bot.send_message(dev_id, text, parse_mode=ParseMode.HTML)
        raise
    

    def detect_intent(self, text, session):
        text_input = df.types.TextInput(text=text, language_code=self.language_code)
        query_input = df.types.QueryInput(text=text_input)
        response = self.session_client.detect_intent(session=session, query_input=query_input)
        return response


@click.command()
@click.argument('tg_token', envvar='TG_TOKEN')
@click.argument('project_id', envvar='PROJECT_ID')
@click.argument('admins', envvar='ADMINS')
@click.option('--language_code', default='ru')
@click.option('--db_path', default='/tmp/local.db')
def run(tg_token, project_id, admins, language_code, db_path):
    session_client = df.SessionsClient()
    bot = Bot(project_id=project_id, language_code=language_code, tg_token=tg_token, admins=admins, db_path=db_path)
    bot.run()
    
if __name__ == '__main__':
    run()
