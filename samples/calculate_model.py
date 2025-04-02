import json
from myabcm_corporate_client_api import CorporateServer
# --------------------------------------------------------------------------------------
# This sample uses the myabcm_corporate_client_api package from Python Package index.
# If you want to use the source code of the package direcly for debugging/improving it,
# COMMENT the line above importing CorporateSever from myabcm_corporate_client_api
# and UNCOMMENT the 5 lines of code below
# --------------------------------------------------------------------------------------

#import platform
#module_dir = os.path.abspath("../src/myabcm_corporate_client_api")
#if module_dir not in sys.path:
#    sys.path.append(module_dir)
#from corporate_server_module import CorporateServer

try:
    # Read credentials from disk (credentials.json)
    with open('credentials.json', 'r', encoding='utf-8') as file:
        credentials = json.load(file)

    # Create CorporateServer object
    corporate_server = CorporateServer(credentials.get("server"), credentials.get("username"), credentials.get("password"))

    # Logon to MyABCM Corporate
    corporate_server.logon()

    # Select MDL-SAMPLE model
    corporate_server.select_model("MDL-SAMPLE")

    # Calculate the association 01/ACTUAL
    corporate_server.calculate_model( "01",  "ACTUAL", False)

    # Logoff from server
    corporate_server.logoff()

except Exception as e:
    print(f"\n\nSCRIPT ERROR: {e}")