import os
import sys
import json
from myabcm_corporate_client_api import CorporateServer

# --------------------------------------------------------------------------------------
# This sample uses the myabcm_corporate_client_api package from Python Package index.
# If you want to use the source code of the package direcly for debugging/improving it,
# COMMENT the line above importing CorporateSever from myabcm_corporate_client_api
# and UNCOMMENT the 5 lines below
# --------------------------------------------------------------------------------------
#import platform
#module_dir = os.path.abspath("../src/myabcm_corporate_client_api")
#if module_dir not in sys.path:
#    sys.path.append(module_dir)
#from corporate_server_module import CorporateServer

# Variables used in the script
model_reference =  "MDL-TEST-MODEL-PYTHON-TEST"
script_reference =  "Script01"

try:
    # Read credentials from disk (credentials.json)
    with open('credentials.json', 'r', encoding='utf-8') as file:
        credentials = json.load(file)

    # Create CorporateServer object
    corporate_server = CorporateServer(credentials.get("server"), credentials.get("username"), credentials.get("password"))

    # Logon to MyABCM Corporate
    corporate_server.logon()

    # Check if model exists
    if not corporate_server.model_exists(model_reference):
        print(f"Sample model {model_reference} not found.")
        print(f"This sample script assumes there is a model with reference {model_reference} that contains the script {script_reference}.")
        print(f"Run the sample import_model.py first to create and import the sample model")
        sys.exit()

    # Select the model
    corporate_server.select_model(model_reference)

    # Execute script
    corporate_server.execute_script(script_reference)

    # Logoff from server
    corporate_server.logoff()

except Exception as e:
    print(f"\n\nSCRIPT ERROR: {e}")
