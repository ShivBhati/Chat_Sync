from bs4 import BeautifulSoup
import json
import pandas as pd
import requests
def upload_data_to_database(id,data):
    sorted_data = sorted(data, key=lambda x: x["Type"])
    # sorted_json = json.dumps(sorted_data, indent=4)
    # print('json data creatd')
    # print(f'sorted data {sorted_json}')
    df = pd.DataFrame(sorted_data)
    print('df created')
    df.rename(columns={
        "SrNo": "field_102",
        "Category": "field_93",
        "Rule": "field_99",
        "Type": "field_98"
    }, inplace=True)
    # print('column renamed')
    df['field_96'] = id
    # Convert DataFrame back to list of dictionaries


    updated_data = df.to_dict(orient='records')
    print(updated_data)
    app_id = "API_ID"
    api_key = "API_Key"
    url = f'https://api.knack.com/v1/objects/object_10/records'

    headers = {
        'X-Knack-Application-ID': app_id,
        'X-Knack-REST-API-Key': api_key,
        'Content-Type': 'application/json'
    }
    type = ''
    Sno = 1
    status = 0
    for record in updated_data:
        if type != record['field_98']:
            Sno = 1
            record['field_102'] = Sno
            type = record['field_98']
        else:
            Sno += 1
            record['field_102'] = Sno
        response = requests.post(url, headers=headers, json=record)
        if response.status_code == 200:
            print(f"Record updated successfully.")
            if status == 1:
                status = 1
            else:
                status = 0
        else:
            print(f"Failed to update record. Response: {response.text}")
            status = 1

    return status
