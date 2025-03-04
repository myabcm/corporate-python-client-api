import os
import sys
import json
#from myabcm_corporate_client_api import CorporateServer

# --------------------------------------------------------------------------------------
# This sample uses the myabcm_corporate_client_api package from Python Package index.
# If you want to use the source code of the package direcly for debugging/improving it,
# COMMENT the line above importing CorporateSever from myabcm_corporate_client_api
# and UNCOMMENT the 5 lines of code below
# --------------------------------------------------------------------------------------

#import platform
module_dir = os.path.abspath("../src/myabcm_corporate_client_api")
if module_dir not in sys.path:
    sys.path.append(module_dir)
from corporate_server_module import CorporateServer

# Variables used in the execute_script
model_name =  "Test Model (Python test)"
model_reference =  "MDL-TEST-MODEL-PYTHON-TEST"
model_description =  "My Test Model created from a Python script"

try:
    # Read credentials from disk (credentials.json)
    with open('credentials.json', 'r', encoding='utf-8') as file:
        credentials = json.load(file)

    # Create CorporateServer object
    corporate_server = CorporateServer(credentials.get("server"), credentials.get("username"), credentials.get("password"))

    # Logon to MyABCM Corporate
    corporate_server.logon()

    # Check if model exists
    if corporate_server.model_exists(model_reference):
        # A model with the same reference already exists, check with user if we should replace it
        response = input(f"Model using reference {model_reference} already exists. Do you want to replace it? (y/n)").strip().lower()
        if response == 'y':
            # Remove existing model
            corporate_server.remove_model(model_reference);
        else:
            # Cancel the script
            print("Script cancelled.")
            sys.exit()

    # Create a new model with the reference MDL-TST-MODEL
    corporate_server.add_model(model_name, model_reference, model_description, 0)

    # Logoff from server
    corporate_server.logoff()

except Exception as e:
    print(f"\n\nSCRIPT ERROR: {e}")