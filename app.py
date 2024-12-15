from flask_cors import CORS
from flask import Flask, request, jsonify, render_template, url_for, redirect
from flask_babel import Babel, _

import os, sys, requests
import boto3, json
import argparse
from dotenv import load_dotenv
from botocore.exceptions import ClientError
import os.path
from pprint import pp
from configurator.main import Configurator
from logger.main import Logger
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

def get_secret():

    secret_name = "openai/api-key"
    region_name = "us-west-2"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

    secret = get_secret_value_response['SecretString']

    return secret

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

openai_key = get_secret()
openai_key = get_openai_key()
os.environ['OPENAI_API_KEY'] = openai_key

# Open the API Key from the .env file
#if not is_running_on_ec2():
#    print("Running on local host...")
#    load_dotenv(".env", override=True)
#else:
#    print("Running in on EC2...")
#    openai_key = get_openai_key()
#    os.environ['OPENAI_API_KEY'] = openai_key
os.environ['USER_AGENT'] = 'myagent'

# initiate the loggers
fbackLog = Logger(prefix = "feedback")
ctactLog = Logger(prefix = "contact")

# instantiate
conv_chat = slaGPT(prompt_strings[PROMPT_CONVERSATION],model_vstore,model_name)
conv_chat.set_prompt_items(item_strings[PROMPT_CONVERSATION])

app = Flask(__name__)
CORS(app)

# Configuration for supported languages
app.config['BABEL_DEFAULT_LOCALE']          = 'nl'
app.config['BABEL_SUPPORTED_LOCALES']       = ['nl', 'en']
app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'

babel = Babel(app)

#def get_locale():
#  return 'fr'

def get_locale():
    # Check if the 'locale' cookie exists
    user_locale = request.cookies.get('locale')
    if user_locale in app.config['BABEL_SUPPORTED_LOCALES']:
        return user_locale
    return request.accept_languages.best_match(app.config['BABEL_SUPPORTED_LOCALES'])

babel.init_app(app, locale_selector=get_locale)


def llm_response(input_message,conversation_id,project_id):
    if project_id == "None" or project_id == "none":
        input_filter = None
    else:
        input_filter = {'pid': project_id}

    output_message, _ = conv_chat.conversation(input_message,input_filter,conversation_id,False)
    
    return output_message

# Route to serve the HTML page
@app.route("/")
def index():
    return render_template("index.html")  # Assumes index.html is in the 'templates' folder

@app.route('/home')
def goto_home():
    return redirect(url_for('index') + '#home')

@app.route('/about')
def goto_about():
    return redirect(url_for('index') + '#about')

@app.route('/services')
def goto_services():
    return redirect(url_for('index') + '#services')

@app.route('/usecases')
def goto_usecases():
    return redirect(url_for('index') + '#usecases')

@app.route('/testimonials')
def goto_testimonials():
    return redirect(url_for('index') + '#testimonials')

@app.route('/contact')
def goto_contact():
    return redirect(url_for('index') + '#contact')

@app.route("/usecase-1")
def usecase1():
    return render_template("usecase-1.html")  # Assumes index.html is in the 'templates' folder

@app.route('/change-language/<lang>')
def change_language(lang):
    if lang in app.config['BABEL_SUPPORTED_LOCALES']:
        response = redirect(url_for('index'))
        response.set_cookie('locale', lang)  # Set the 'locale' cookie
        return response
    return redirect(url_for('index'))

@app.route("/", methods=["POST"])
def process_message():
    data            = request.get_json()
    post_type       = data.get("post_type")
    message         = data.get("message")
    conversation_id = data.get("conversation_id")
    project_id      = data.get("project_id")

    # Process the message here (e.g., perform calculations, send notifications, etc.)

    # Return a response as JSON
    if post_type == "LLM":
        output_message = llm_response(message,conversation_id,project_id)

    if post_type == "CONTACT":
        output_message = "Contact Information received, thank you."
        msg = f"{conversation_id};{message}"
        ctactLog.log("CONTACT",msg)

    if post_type == "FBACK":
        output_message = "Feedback received, thank you."
        msg = f"{conversation_id};{message}"
        fbackLog.log("FEEDBACK",msg)
    
    print(f"POST type received      : {post_type}")
    print(f"input message received  : {message}")
    print(f"conversation id received: {conversation_id}")
    print(f"project id received     : {project_id}")
    print(f"output message returned : {output_message}")
    
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
