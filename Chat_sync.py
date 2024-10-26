import time
import os
from openai import OpenAI
from flask import Flask, request, jsonify
import requests
from upload_data import upload_data_to_database
import json
import threading

app = Flask(__name__)


def upload_data_to_knack(id, summary, error):

    app_id = "api_id"
    api_key = "yor_api_id"
    field_key_1 = "field_12"
    field_key_2 = "field_33"
    record_id = id

    url = f"https://api.knack.com/v1/objects/object_2/records/{record_id}"

    data = {
        field_key_1: summary,
        field_key_2: error
    }


    headers = {
        "X-Knack-Application-Id": app_id,
        "X-Knack-REST-API-Key": api_key,
        "Content-Type": "application/json"
    }
    attempt = ''
    max_attempts = 3

    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.put(url, json=data, headers=headers)
            response.raise_for_status()

            # If the request is successful, print the response and break the loop
            print("Data uploaded successfully:", response.json())
            break

        except requests.exceptions.HTTPError as http_err:
            print(f"Attempt {attempt} - HTTP error occurred: {http_err}")
        except Exception as err:
            print(f"Attempt {attempt} - An error occurred: {err}")

        time.sleep(3)

    if attempt == max_attempts:
        print("All attempts to upload data failed.")


def process_data_pdftool(data):
    fileURL = data['file']
    id = data["id"]

    print(id)
    stime = time.time()
    strtime = str(stime) + '_file'

    response = requests.get(fileURL, timeout=60)
    file_name = data['file_name']

    initial_filepath = f'C:\\Code_support\\Guideline_Chat_Sync\\pdftool\\Unparsed\\{file_name}'
    filename = f'C:\\Code_support\\Guideline_Chat_Sync\\\pdftool\\web\\{file_name}'

    with open(filename, "wb") as file:
        file.write(response.content)

    while True:
        if os.path.isfile(filename):
            time.sleep(15)
            query = 'You are an ebilling guideline legal expert. Please read through all the pages in the pdf document.  Analyze all the billing guidelines in an exhaustive manner including fees, costs, data security and other rules the client must follow in the guidelines. Make sure you do not miss any rules in your analysis. Please return in json format with fields: SrNo, Category, Rule, Type(Fee or Cost or Data Security or Other Charges)'
            client = OpenAI(
                # api_key= 'YOUR_API_KEY',
            )

            file = client.files.create(
                file=open(filename, "rb"),
                purpose='assistants'
            )
            vector_store = client.beta.vector_stores.create(name="PDF Analysis")
            # Ready the files for upload to OpenAI
            file_paths = [filename]
            file_streams = [open(path, "rb") for path in file_paths]
            # Use the upload and poll SDK helper to upload the files, add them to the vector store,
            # and poll the status of the file batch for completion.
            file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
                vector_store_id=vector_store.id, files=file_streams
            )
            fileid = file.id

            assistant = client.beta.assistants.create(
                name="PDF Analyzer",
                description="You are great at reading PDF documents and answering the questions on PDF.",
                model="gpt-4o",
                tools=[{"type": "file_search"}],
                tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
                temperature=1,
                top_p=1
            )

            thread = client.beta.threads.create(
                messages=[
                    {
                        "role": "user",
                        "content": query,
                        "attachments": [
                            {
                                "file_id": fileid,
                                "tools": [{"type": "code_interpreter"}]
                            }
                        ]
                    }
                ]
            )

            run = client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=assistant.id,
                temperature=1,
                top_p=1
            )

            while run.status != "completed":
                run = client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
                print(run.status)
                time.sleep(2)

            messages = client.beta.threads.messages.list(
                thread_id=thread.id
            )
            print('data fetched')
            Answer = messages.data[0].content[0].text.value
            Answer = Answer.replace('[Download PDF]', '{Download PDF}')
            print(Answer)
            record_status = ''
            try:
                if Answer[Answer.index("["):Answer.index("]") + 1]:
                    print('json data found')
                    answertoreturn = Answer[Answer.index("["):Answer.index("]") + 1]
                    data = json.loads(answertoreturn)
                    record_status = ''
                    status = upload_data_to_database(id, data)
                    if status == 0:
                        record_status = ''
                        record_status = 'Analysis Complete'
                        error = ''
                        upload_data_to_knack(id, record_status, error)
                    else:
                        record_status = ''
                        record_status = 'Please Reanalyze'
                        error = ''
                        upload_data_to_knack(id, record_status, error)
            except Exception as e:
                print(f"Printing data in else part {data}")
                record_status = ''
                record_status = 'Please Reanalyze'
                error = data
                upload_data_to_knack(id, record_status, error)
            break

        else:
            print('Finding pdf file')
            time.sleep(2)

    return 'answertoreturn'


@app.route('/pdfwebhook/', methods=['POST'])
def pdfwebhook():
    data = request.json
    response = jsonify({"message": "Data received"}), 200
    threading.Thread(target=process_data_pdftool, args=(data,)).start()
    status = 'data sucessfully received by endpoint'
    return response


@app.route('/webhook/', methods=['POST'])
def webhook():
    data = request.json
    # threading.Thread(target=process_data_webhook, args=(data,)).start()
    fileURL = data['file']

    stime = time.time()
    strtime = str(stime) + '_file'

    response = requests.get(fileURL)

    filename = strtime + "_data.pdf"

    with open(filename, "wb") as file:
        file.write(response.content)

    query = data.get("question")

    client = OpenAI(
        # api_key="your_api_id",
    )

    file = client.files.create(
        file=open(filename, "rb"),
        purpose='assistants'
    )
    fileid = file.id

    assistant = client.beta.assistants.create(
        name="Data Analyzer",
        description="You are great at analyzing the data and answering the questions on data.",
        model="gpt-4o",
        tools=[{"type": "code_interpreter"}],
        tool_resources={
            "code_interpreter": {
                "file_ids": [fileid]
            }
        }
    )

    thread = client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": query,
                "attachments": [
                    {
                        "file_id": fileid,
                        "tools": [{"type": "code_interpreter"}]
                    }
                ]
            }
        ]
    )

    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id
    )

    while run.status != "completed":
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )
        print(run.status)
        time.sleep(2)

    messages = client.beta.threads.messages.list(
        thread_id=thread.id
    )

    return messages.data[0].content[0].text.value

if __name__ == '__main__':
    app.run(debug=True,port=5000)
