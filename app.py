from flask_cors import CORS
from flask import Flask, request, jsonify, render_template

import os, sys, requests
import boto3, json
import argparse
from dotenv import load_dotenv
import os.path
from pprint import pp
from configurator.main import Configurator
from agtSLA.main import slaGPT

APP_NAME          = "appbackend_lang.py"
APP_DESCRIPTION   = "Backend Langchain app"
APP_EPILOG        = ""

PROMPT_CONVERSATION = 0

# %%
# parsing the configuration file
def is_running_in_vscode(): return 'VSCODE_PID' in os.environ

def is_running_on_ec2():
    # check for EC2 metadata
    try:
        response = requests.get("http://169.254.169.254/latest/meta-data/", timeout=1)
        return response.status_code == 200
    except requests.RequestException:
        return False

def get_openai_key():
    client = boto3.client('secretsmanager', region_name='us-west-2')
    response = client.get_secret_value(SecretId='openai/api-key')
    secret = json.loads(response['SecretString'])
    return secret['OPENAI_API_KEY']

if is_running_in_vscode(): sys.argv = [APP_NAME, '--verbose','config_elzenbos.yml']
else: print("Not running in Visual Studio Code")

parser = argparse.ArgumentParser(
    prog        = APP_NAME,
    description = APP_DESCRIPTION,
    epilog      = APP_EPILOG)

parser.add_argument('-v', '--verbose', action='store_true', help='Increase output verbosity')
parser.add_argument('config', type=str, help='Path to the configuration file')

args, _ = parser.parse_known_args()


# %%
# configuration file parser
# https://tinztwins.hashnode.dev/constructing-a-chatgpt-like-app-using-langchain-and-plotly-dash
# prepare parser
configParser = Configurator(args.config)
if configParser is None:
    sys.exit()

# default values
app_sources   = False
model_name    = "gpt-4o"
model_temp    = 0
app_greeting  = "Hi,"

# read parser
context_name    = configParser.get('context', 'symbol')
if context_name is None:
    print(f"ERROR - no context name provided")
    sys.exit()
context_name   = context_name.lower()

model_name      = configParser.get_with_default('model','name','gpt-4o').lower()
model_vstore    = configParser.get_with_default('context','vstore','vstore').lower().replace("{symbol}",context_name)
model_temp      = int(configParser.get_with_default('model','temperature','0').lower())


app_sources    = configParser.get('application', 'sources').lower() == "true"

app_greeting   = configParser.get('application', 'greeting')


prompts = configParser.get_list("application","prompts")
if prompts is None:
    print(f"ERROR - no application prompts provided")
    sys.exit()

# TODO
prompts = map(str.strip, prompts)

prompt_strings = []
for p in prompts: prompt_strings.append([configParser.get(p,"system"),configParser.get(p,"history"),configParser.get(p,"user")])

items = configParser.get("application","promptitems").split(",")
items = map(str.strip, items)
item_strings = []
for i in items: item_strings.append(dict(configParser.items(i)))

del(prompts,items)
del(i,p)

if args.verbose:
    pp(model_name)
    pp(model_vstore)
    pp(prompt_strings)
    pp(item_strings)

# Open the API Key from the .env file
if not is_running_on_ec2():
    print("Running on local host...")
    load_dotenv(".env", override=True)
else:
    print("Running in on EC2...")
    openai_key = get_openai_key()
os.environ['USER_AGENT'] = 'myagent'

# instantiate
conv_chat = slaGPT(prompt_strings[PROMPT_CONVERSATION],model_vstore,model_name)
conv_chat.set_prompt_items(item_strings[PROMPT_CONVERSATION])

app = Flask(__name__)
CORS(app)


def llm_response(input_message):
    output_message, _ = conv_chat.conversation(input_message)
    return output_message

# Route to serve the HTML page
@app.route("/")
def index():
    return render_template("index.html")  # Assumes index.html is in the 'templates' folder

@app.route("/", methods=["POST"])
def process_message():
    data            = request.get_json()
    post_type       = data.get("post_type")
    message         = data.get("message")
    conversation_id = data.get("conversation_id")

    # Process the message here (e.g., perform calculations, send notifications, etc.)

    # Return a response as JSON
    # TODO - add a conversation id
    #response = {
    #    "response": llm_response(message) + "\n message from id: " + conversation_id,
    #    # Add other response data as needed
    #}
    output_message = llm_response(message)

    if args.verbose:
        print(f"POST type received      : {post_type}")
        print(f"input_message  received : {message}")
        print(f"conversation id received: {conversation_id}")
        print(f"output_message  returned: {output_message}")


    response = {
        "response": output_message,
        # Add other response data as needed
    }
    return jsonify(response)

if __name__ == "__main__":
    app.run(debug=True)

# gracefully end
print("Bye...")
sys.exit(0)    
