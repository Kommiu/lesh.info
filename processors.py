processor_map = dict()


def process_default(response, update, context):
    response_lines = response.query_result.fulfillment_text.split('\n')
    for line in response_lines:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=line,
        )

