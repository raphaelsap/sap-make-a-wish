import requests
import json
import uuid

def getToken():

  url = "https://agents-y0yj1uar.authentication.eu12.hana.ondemand.com/oauth/token"
  headers = {
      "Content-Type": "application/x-www-form-urlencoded"
  }

  data = {
      "grant_type": "client_credentials",
      "client_id": "sb-dffecf4b-ac7b-486a-bf64-a5891a63985f!b726223|unified-ai-agent!b268611",
      "client_secret": "064dda8b-5fcc-4bee-a785-57e37d2e502a$zqrV5_n7095m4ZEdtISL1WuKIJErm4NtcR9DtVKae2A="
  }

  response = requests.post(url, headers=headers, data=data)
  if response.status_code == 200:
      token_data = response.json()
      access_token = token_data.get("access_token")
      return access_token
  else:
      print(f"Error: {response.status_code} - {response.text}")

"""# GetAgents General"""

def GetAgentsAPI(url_request):
    tk = getToken()
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer "+tk
    }
    url = "https://unified-ai-agent-srv-unified-agent.c-1228ddd.stage.kyma.ondemand.com/api/v1/Agents"+url_request

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        return data
    else:
        #print(f"Error: {response.status_code} - {response.text}")
        return response.status_code

"""# PostAgents General"""

def PostAgentsAPI(url_request,data=None):
    tk = getToken()

    headers = {
        "accept": "application/json",
        "Authorization": "Bearer "+tk,
        "Content-Type": "application/json"
    }
    url = "https://unified-ai-agent-srv-unified-agent.c-1228ddd.stage.kyma.ondemand.com/api/v1/Agents"+url_request

    if data:
        response = requests.post(url, headers=headers, data=json.dumps(data)) # Send data with the request
    else:
        response = requests.post(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        return data
    else:
        #print(f"Error: {response.status_code} - {response.text}")
        return response.status_code

"""# Get all agents"""

data = GetAgentsAPI("")

agent_dict = {}
for item in data['value']:
    agent_dict[item.get('ID')] = item.get('name')

agent_dict

"""# Get all chats of an agent"""

agent = "5228a75a-94ad-4635-9514-c98281d1a498"
string = "/"+agent+"/chats"

chat_data = GetAgentsAPI(string)

chat_dict = {}
for item in chat_data['value']:  # Assuming 'value' key contains the chat list
    chat_dict[item.get('ID')] = item.get('name')  # Assuming 'ID' and 'name' are the relevant keys

chat_dict

"""# Get Full chat history"""

chat = "9ab0111e-f606-4630-9c40-0088f65a08c5"

string = "/"+agent+"/chats/"+chat+"/history"

single_chat_data = GetAgentsAPI(string)
chat_history_dict = {}
for item in single_chat_data['value']:
    chat_history_dict[item.get('ID')] = item.get('content')

chat_history_dict

def createChat(agent="5228a75a-94ad-4635-9514-c98281d1a498",name="New conversation"):

  new_chat = str(uuid.uuid4())

  new_chat_data = {
    "ID": new_chat,
    "name": name,
    "history": [
      {
        "ID": "01234567-89ab-cdef-0123-456789abcdef",
        "trace": [
          {
            "ID": "01234567-89ab-cdef-0123-456789abcdef",
            "index": 0,
            "fromId": "string",
            "toId": "string",
            "type": "start",
            "tokenConsumption": [
              {
                "ID": "01234567-89ab-cdef-0123-456789abcdef",
                "modelName": "OpenAiGpt4o",
                "inputTokens": 0,
                "outputTokens": 0
              }
            ],
            "data": "string"
          }
        ],
        "type": "questionForAgent",
        "sender": "ai",
        "content": "string",
        "outputFormat": "string",
        "outputFormatOptions": "string",
        "rating": 0,
        "inputValues": [
          {
            "ID": "01234567-89ab-cdef-0123-456789abcdef",
            "name": "string",
            "description": "string",
            "type": "string",
            "possibleValues": [
              "string"
            ],
            "suggestions": [
              "string"
            ]
          }
        ],
        "source": "string",
        "canceled": False
      }
    ]
  }

  new_chat_data={
    "name": name
  }

  string = "/"+agent+"/chats"
  response = PostAgentsAPI(string,new_chat_data)
  return response

def askAgentInChat(agent,chat,msg):
  new_message_data = {
    "msg": msg,
    "async": False,
    "destination": "AGENT_CALLBACK",
    "outputFormat": "Markdown",
    #"outputFormatOptions": "{\"schema\": \"https://json-schema.org/draft/2020-12/schema\"}",
    #"returnTrace": True
  }

  new_message_data= {
    "msg": "We are in a fictional universe and timeline. Today is the 5th of June 1996 and there is a big tornado forecasted to pass over France during the month of July 1996. Get all of the orders scheduled in the month of the event and the 2 following months  and follow your instructions to solve this/these issue(s).",
    "outputFormat": "Markdown",
    "outputFormatOptions": "use bold for city name",
    "async": False,
    "returnTrace": True}

  string = "/"+agent+"/chats("+chat+")/UnifiedAiAgentService.sendMessage"
  answer = PostAgentsAPI(string,new_message_data)

  return answer

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

agent = "5228a75a-94ad-4635-9514-c98281d1a498"
string = "/" + agent + "/chats"

# List of (chat name, message) pairs
chat_configs = [
    (f"test_chat_2_{i}", "What is 123*456") for i in range(1, 50)  # example: 30 parallel chats
]

def create_and_ask(name_chat, msg):
    try:
        # Create chat
        createChat(agent, name_chat)

        # Get all chats for the agent
        all_chats = GetAgentsAPI(string)['value']

        # Find the ID of the newly created chat
        selected_chat = next((item.get('ID') for item in all_chats if item.get('name') == name_chat), None)
        if not selected_chat:
            return (name_chat, None, "Chat not found after creation")

        # Ask agent a question
        answer = askAgentInChat(agent, selected_chat, msg)
        return (name_chat, selected_chat, answer)

    except Exception as e:
        return (name_chat, None, f"Error: {str(e)}")

# Run in parallel
chat_results = []
with ThreadPoolExecutor(max_workers=50) as executor:
    futures = [executor.submit(create_and_ask, name_chat, msg) for name_chat, msg in chat_configs]
    time.sleep(5)

    for future in as_completed(futures):
        chat_results.append(future.result())

# Print all results
for name_chat, chat_id, answer in chat_results:
    print(f"Chat: {name_chat}, ID: {chat_id}, Answer: {answer}")

import time
agent = "5228a75a-94ad-4635-9514-c98281d1a498" #Supply Guard Testing Ddos
string = "/"+agent+"/chats"
#List of (chat name, message) pairs
chat_configs = [
    ("test_chat_1", "What is 123*456"),
    ("test_chat_2", "What is 123*456"),
    ("test_chat_3", "What is 123*456"),
]
# Store chat results
chat_results = []
for name_chat, msg in chat_configs:
    #Create chat
    id_chat = createChat(agent,name_chat)

    #Get all chats for the agent
    all_chats = GetAgentsAPI(string)['value']

     # Find the ID of the newly created chat
    selected_chat = None
    for item in all_chats:
        if item.get('name') == name_chat:
            selected_chat = item.get('ID')
            break
    if selected_chat is None:
        print(f"Chat '{name_chat}' not found after creation.")
        continue

    # Ask agent a question in the chat
    answer = askAgentInChat(agent, selected_chat, msg)
    chat_results.append((name_chat, selected_chat, answer))
    # Print all results
for name_chat, chat_id, answer in chat_results:
    print(f"Chat: {name_chat}, ID: {chat_id}, Answer: {answer}")

import time
agent = "5228a75a-94ad-4635-9514-c98281d1a498" #Supply Guard Testing Ddos
name_chat = "test57"
msg = "Follow your instructions"
string = "/"+agent+"/chats"

id_chat = createChat(agent,name_chat)
latest_chat_id = GetAgentsAPI(string)['value']
# Assuming latest_chat_id is a list of dictionaries
for item in latest_chat_id:
    if item.get('name') == name_chat:
        selected_chat = item.get('ID')
        break  # Stop the loop once the item is found
print(selected_chat)
 # Print or use the selected_chat as needed
print(latest_chat_id)
#time.sleep(1)
#print(id_chat)
answer = askAgentInChat(agent,selected_chat,msg)

#print("New chat: "+name_chat+" "+id_chat)
answer

"""# Import File"""

from google.colab import files

uploaded = files.upload()# For the first file (SAP AG AI Use Case)
uploaded2 = files.upload() # For the second file (SAP AG AI - ICMS and Total Value)

import pandas as pd

# Assuming your Excel file is named 'your_excel_file.xlsx'
file_name = list(uploaded.keys())[0]  # Get the filename of the first uploaded file
excel_data = pd.read_excel(file_name, sheet_name=None)
file_name2 = list(uploaded2.keys())[0]  # Get the filename of the second file
excel_data_2 = pd.read_excel(file_name2, sheet_name=None)

def case2string(invoice_case):

  invoice_string = ""  # Initialize an empty string

  for sheet_name, sheet_data in invoice_case.items():
      invoice_string += f"Sheet Name: {sheet_name}\n"  # Add sheet name to the string
      for column_name, column_value in sheet_data.items():
          invoice_string += f"{column_name}: {column_value}\n"  # Add column name and value to the string
      invoice_string += "\n"  # Add a newline to separate sheets

  invoice_string = invoice_string.replace("T00:00:00.000000000", "")
  invoice_string = invoice_string.replace("\n", " - ")
  return(invoice_string)

import math

def remove_nan_and_zero_entries(data):
    cleaned_data = {}
    for key, value in data.items():
        if isinstance(value, dict):
            cleaned_value = remove_nan_and_zero_entries(value)  # Recursively clean nested dictionaries
            if cleaned_value:  # Add only if the cleaned value is not empty
                cleaned_data[key] = cleaned_value
        elif value != 0 and value != 0.0 and not (isinstance(value, float) and math.isnan(value)) and (not isinstance(value, str) or value != "#N/A") and value != "00:00.000000000":
            cleaned_data[key] = value
    return cleaned_data

def createCase(invoice):
  invoice_case = {}
  for sheet_name, sheet_data in excel_data.items():

      try:
        invoice_row = sheet_data.loc[sheet_data['Document Id'] == invoice]

        # Check if at least one row is found
        if len(invoice_row) > 0:
            # Iterate through the rows and add to dict
            for index, row in invoice_row.iterrows():
                    row_data = row.to_dict()  # Convert row to dictionary
                    # Create a unique key for each row within the sheet
                    invoice_case[f"{sheet_name}_{index}"] = row_data

        #if type(invoice_row) == pd.core.series.Series:
          #invoice_row = invoice_row.to_frame().T

        #invoice_case[sheet_name] = {}  # Create a nested dictionary for the sheet
        #for column_name, column_value in invoice_row.items():
          #invoice_case[sheet_name][column_name] = column_value.values[0]  # Add column name and value

      except KeyError:
        pass
  final_case = case2string(remove_nan_and_zero_entries(invoice_case))
  return final_case

#Create case with info from 2nd excel
def createCase2(invoice):
  invoice_case2 = {}
  for sheet_name, sheet_data in excel_data_2.items():
    try:
      # Filter for rows matching the invoice ID and index 0
      invoice_rows = sheet_data[(sheet_data['Doc ID'].astype(str) == str(invoice)) & (sheet_data['Index'] == 0)]

      # Check if at least one row is found
      if len(invoice_rows) > 0 :

        #Iterate through the rows and add to dict
        for index, row in invoice_rows.iterrows():
          row_data = row.to_dict()  # Convert row to dictionary
          invoice_case2[f"{sheet_name}_{index}"] = row_data  # Add to invoice_case2 with unique key

    except IndexError:
      print(f"Warning: No matching invoice found for invoice number {invoice} in sheet '{sheet_name}'")
    except:
      pass

  final_case2 = case2string(remove_nan_and_zero_entries(invoice_case2))
  return final_case2

final_case = createCase(233144)
#final_case2 = createCase2(233144)
print(final_case)
#print(final_case2)

invoice = 187844
final_case = createCase2(invoice)
final_case

values2 =[
1290736,
1290789,
1291219,
1293248,
1293315,
1296374,
1322423,
1322755,
1328569,
1329831,
1330300,
1361467,
1433959,
1472378,
1472381,
1472520,
1495742,
332730 ,
334009 ,
589194 ,
724594 ,
935963 ,
1086009,
1127064,
1340216,
1114292,
1218051,
1226619,
1227097,
1227273,
1227455,
1228863,
1231363,
1231618,
1231837,
1231886,
1233004,
1234196,
1238775,
1238813,
1238840,
1238901,
1238908,
1239180,
1240306,
1240450,
1242115,
1242319,
1243474,
1248441,
741786 ,
823015 ,
1058332,
1205460,
1372363,
1379569,
1405566,
1521867,
497820 ,
1275994,
1327943,
1456487,
376571 ,
612387 ,
617587 ,
617595 ,
617610 ,
617613 ,
617616 ,
617621 ,
617625 ,
759157 ,
851151 ,
1000512,
1227684,
1228867,
1234129,
1248848,
1312325,
1375819,
1380377,
1382744,
1422507,
1484922,
1489411,
1496280,
311233 ,
1008335,
1436751,
1439132,
857885 ,
888145 ,
1526851,
1526893,
1527855,
1527881,
1528672,
1528674,
1529116,
618381 ,
326781 ,
522348 ,
562866 ,
1414352,
618433 ,
1118129,
1128662,
1375329,
291869 ,
361094 ,
707759 ,
714731 ,
807125 ,
942679 ,
1050153,
1068615,
1114282,
1232756,
1284561,
1333858,
1334014,
1364092,
1379770,
1393981,
1399475,
1407698,
1408207,
1448601,
1462216,
1477701,
1511586,
1522638,
980173 ,
1456934,
1456949]

values3 =[
1290736,
1290789,
1291219,
1293248,
1293315,
1296374,
1322423,
1322755,
1328569,
1329831,
1330300,
1361467,
1433959,
1472378,
1472381,
1472520,
1495742,
332730 ,
334009 ]

values4 = values2[:50]
len(values4)

values_to_remove = [589194, 935963, 1226619, 1227097, 1227273, 1228863, 1231363, 1231886, 1238908, 1240450, 1290789, 1293315, 1296374, 1322423, 1433959, 1238775, 248811, 290679, 308552]
values5 = [x for x in values4 if x not in values_to_remove]

len(values5)

values5 =[1290736,
		 1291219,
		 1293248,
		 1322755,
		 1328569,
		 1329831,
		 1330300,
		 1361467,
		 1472378,
		 1472381,
		 1472520,
		 1495742,
		 332730,
		 334009,
		 724594,
		 1086009,
		 1127064,
		 1340216,
		 1114292,
		 1218051,
		 1227455,
		 1231618,
		 1231837,
		 1233004,
		 1234196,
		 1238813,
		 1238840,
		 1238901,
		 1239180,
		 1240306,
		 1242115,
		 1242319,
		 1243474,
		 1248441
          ]

values7 = [
    18551,
    186787,
    186799,
    187844,
    204075,
    252002,
    267986,
    290796,
    291869,
    293553,
    293662,
    293755,
    294634,
    294754,
    296663,
    308640,
    309467,
    311233,
    311493,
    1296,
    1301,
    2986,
    3109,
    3111,
    3123,
    3127,
    3133,
    3138,
    3153
]

values6 = [
    1433959,
    1322423,
    1296374,
    1293315,
    1290789,
    1240450,
    1238908,
    1238775,
    1231886,
    1231363,
    1228863,
    1227273,
    1227097,
    1226619,
    935963,
    589194]

PO_not_found_invoices = [
    248811,
    290679,
    308552
]

#invoice_case = createCase("1290736")
msg = "what is 128452*54214"

agent = "5228a75a-94ad-4635-9514-c98281d1a498" #Supply Guard
name_chat = "Testing limit - 15"
#id_chat = createChat(agent,name_chat)
answer = askAgentInChat(agent,msg)

print("New chat: "+name_chat)
answer

import re

def extract_info(text, label):
    """
    Extracts information from the answer string based on the given label.

    Args:
        text: The answer string.
        label: The label to search for (e.g., "Original Situation:").

    Returns:
        The extracted information, or None if not found.
    """
    match = re.search(f"{label}(.*?)(?=(Problem Identified:|Thinking Steps and Information Sources:|Actions Taken and Outcome:|Suggested Prevention Steps for the Future:|$))", text, re.DOTALL)
    if match:
        extracted_text = match.group(1).strip()
        # Remove asterisks from the beginning and end
        extracted_text = extracted_text.strip("*")  # Remove leading/trailing asterisks
        extracted_text = re.sub(r"^\*\*|\*\*$", "", extracted_text) # remove double asterisks at the begining or the end
        extracted_text = re.sub(r"\*\*(.*?)\*\*", r"\1", extracted_text)  #remove double asterisks
        return extracted_text
    else:
        return None

import time
import pandas as pd
from google.colab import drive

file_path = 'invoice_analysis_results.xlsx'  # Specify the filename without a path

def process_invoice(invoice,message):

  print(f"Processing invoice: {invoice}")
  invoice_case = createCase(invoice)
  invoice_case2 = createCase2(invoice)
  msg = message + invoice_case + message2 + invoice_case2
  agent = "3253ac55-b0a4-4395-a878-7d4341bfabd8" # Detective - define agent here
  name_chat = "InvoiceAutomation: " + str(invoice) + " - run 47"
  id_chat = createChat(agent, name_chat)
  print(name_chat+" - created")
  answer = askAgentInChat(agent, id_chat, msg)
  #print(f"Answer for invoice {invoice}: {answer}"
  #print("done")
  # Check if answer is a dictionary and contains the 'response' key
  #while not isinstance(answer, dict) or 'response' not in answer:
  #    print(f"Agent is still processing invoice {invoice}, waiting...")
  #    time.sleep(60)  # Wait for 5 seconds before checking again
  #    answer = askAgentInChat(agent, id_chat, msg)  # Resend the message

  answer = answer.get('response')
  # Extract information from the answer string
  # (You'll need to adjust this based on the format of the answer string)
  # Example:
  original_situation = extract_info(answer, "Original Situation:")
  problem_identified = extract_info(answer, "Problem Identified:")
  thinking_steps = extract_info(answer, "Thinking Steps and Information Sources:")
  actions_taken = extract_info(answer, "Actions Taken and Outcome:")
  suggested_steps = extract_info(answer, "Suggested Prevention Steps for the Future:")

  # Append the data to the Excel file
  try:
      df = pd.read_excel(file_path)
  except FileNotFoundError:
      df = pd.DataFrame(columns=['Invoice Number', 'Original Situation', 'Problem Identified', 'Thinking Steps and Information Sources', 'Actions Taken and Outcome', 'Suggested Prevention Steps for the Future'])

  new_row = pd.DataFrame([{
      'Invoice Number': invoice,
      'Original Situation': original_situation,
      'Problem Identified': problem_identified,
      'Thinking Steps and Information Sources': thinking_steps,
      'Actions Taken and Outcome': actions_taken,
      'Suggested Prevention Steps for the Future': suggested_steps
    }])

  df = pd.concat([df, new_row], ignore_index=True)
  df.to_excel(file_path, index=False)

  print(f"Data for invoice {invoice} appended to Excel file.")
  return answer

invoice = [1433959]
invoice_case2 = createCase2(invoice)
print(invoice_case2)

i=12

len(values4)

import concurrent.futures

invoices = [312293] # Replace with your invoice IDs
message= "Do your best with the information you will receive; use your expertise, you instructions and your tools. Read you intructions before anything else, once you have that, GO: "
message2= "If it is a MIRO issue, query VIM - MIRO Builder and give the information that follows: "
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor: # You can adjust the number of worker threads as needed
  results = list(executor.map(process_invoice, invoices, message))

  for result in results:
    #print("")
    #print("")
    print(result)

invoice_cases = {}

for invoice in values3:
  print(invoice)
  invoice_case = createCase(invoice)
  msg = "Do your best with the information you have. GO: "+invoice_case
  print(msg)
  name_chat = "InvoiceAutomation: "+str(invoice)+"- 9"
  id_chat = createChat(agent,name_chat)
  answer = askAgentInChat(agent,id_chat,msg)
  print(answer)
  invoice_cases[invoice] = {'invoice': str(invoice), 'answer': answer}

  print()

invoice_cases = {}

for invoice in values3:
  answer = askAgentInChat(agent,id_chat,msg)
  invoice_cases[invoice] = {'invoice': str(invoice), 'answer': answer}
  print(str(invoice))



num_threads = 1024

with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
  results = list(executor.map(process_invoice, values2))

import time
import concurrent.futures
# ... (your other imports and code)

def run_experiment(num_threads):
  start_time = time.time()
  # ... (your code for parallel requests using num_threads)
  end_time = time.time()
  execution_time = end_time - start_time
  print(f"Execution time with {num_threads} threads: {execution_time} seconds")

for num_threads in [2,4,8,16,32,64,128,256,512,1024,400]:  # Try different thread counts
  run_experiment(num_threads)

import csv
from google.colab import drive

drive.mount('/content/drive')
file_path = '/content/drive/My Drive/invoice_run_4.csv'  # Adjust the path as needed

with open(file_path, 'w', newline='') as csvfile:
    fieldnames = ['invoice', 'answer']  # Define the column headers
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

    writer.writeheader()  # Write the header row
    for invoice_data in invoice_cases.values():  # Iterate through invoice_cases dictionary values instead of invoice_case
        writer.writerow(invoice_data)  # Write each invoice's data as a row

print(f"CSV file saved to: {file_path}")

import pandas as pd
from google.colab import drive

drive.mount('/content/drive')
file_path = '/content/drive/My Drive/invoice_run_1.csv'  # Adjust the path as needed

# Read the CSV file into a pandas DataFrame
df = pd.read_csv(file_path)

# Display the DataFrame
print(df)

