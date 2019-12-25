processor_map = dict()

def detect_intent(text, session, session_client, language_code):
    text_input = df.types.TextInput(text=text, language_code=language_code)
    query_input = df.types.QueryInput(text=text_input)
    response = session_client.detect_intent(session=session, query_inpute=query_input)
    return response

def process_default(response, update, context):
    response_lines = response.query_result.fulfillment_text.split('\n')
    for line in response_lines:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=line,
        )

def process_lecturer(response, update, context, session_client, session):
    lecturer = response.query_result.parameters['teacher_name']

    with sqlite3.connect('local.db') as conn:
        c = conn.cursor()
        c.execute('select * from lecturers where l_name==?', (lecturer, ))
        rows = c.fetchall()

    if row is None:
        response = detect_intent('No', session, session_client, langauge_code)
        

