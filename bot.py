import logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)

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
from processors import processor_map, process_default 




def send_typing_action(func):
    """Sends typing action while processing func command."""
    @wraps(func)
    def command_func(update, context, *args, **kwargs):
        context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)
        return func(update, context,  *args, **kwargs)

    return command_func



@send_typing_action
def _respond(
        update,
        context,
        session_client=None,
        project_id=None,
        language_code=None,
):
    if not update.message or not update.message.text:
        return

    df_session_id = context.user_data.get('df_session_id', None)
    if df_session_id is None:
        df_session_id = update.effective_user.id

    df_session = session_client.session_path(project_id, df_session_id)
    text_input = df.types.TextInput(
        text=update.message.text,
        language_code=language_code,
    )
    query_input = df.types.QueryInput(text=text_input)
    response = session_client.detect_intent(
        session=df_session,
        query_input=query_input,
    )

    processor = processor_map.get(
        response.query_result.intent.display_name,
        process_default
    )
    processor(response, update, context)



def error_handler(update, context, devs):
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

@click.command()
@click.argument('tg_token', envvar='TG_TOKEN')
@click.argument('project_id', envvar='PROJECT_ID')
@click.argument('admins', envvar='ADMINS')
@click.option('--language_code', default='ru')
def run(tg_token, project_id, admins, language_code):
    session_client = df.SessionsClient()

    updater = Updater(
        token=tg_token,
        use_context=True,
    )
    dispatcher = updater.dispatcher
    respond = partial(_respond, project_id=project_id, session_client=session_client, language_code=language_code)
    respond_handler = MessageHandler(Filters.text, respond)
    dispatcher.add_handler(respond_handler)
    
    admins = [int(x) for x in admins.split(' ')]
    dispatcher.add_error_handler(partial(error_handler, devs=admins))
    updater.start_polling()

if __name__ == '__main__':
    run()
