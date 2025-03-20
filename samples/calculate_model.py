import os
import sys
import platform

# This sample uses the myabcm_corporate_client_api package from Python Package index.
# If you want to use the source code of the package direcly for debugging/improving it,
# COMMENT the import below and UNCOMMENT the next 4 lines of code after the line below.
from myabcm_corporate_client_api import CorporateServer

#module_dir = os.path.abspath("../src/myabcm_corporate_client_api")
#if module_dir not in sys.path:
#    sys.path.append(module_dir)
#from corporate_server_module import CorporateServer


try:
    # Create CorporateServer object
    corporate_server = CorporateServer("http://myabcm.corporate.instance1/proxy", "john.doe", "myabcm")

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