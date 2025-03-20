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

    # Select MDL-NEW-DEMO-MODEL-PT model
    corporate_server.select_model("MDL-SAMPLE")

    # Remove import just created and executed
    corporate_server.scenario_builder("01", "ACTUAL", "01", "BUDGET", True, {
        "CopyAssignments": True,
        "IncludeDriverQuantity": True,
        "CopyAttributes": True,
        "IncludeAttributeQuantity":  True,
        "EnteredCost": True,
        "OutputQuantity": True,
        "Revenue": True,
        "AssignmentsFactor": 1,
        "AttributesFactor": 1,
        "EnteredCostFactor": 1,
        "OutputQuantityFactor": 1,
        "RevenueFactor": 1,
        "OperationType": 1})

    # Logoff from server
    corporate_server.logoff()

except Exception as e:
    print(f"\n\nSCRIPT ERROR: {e}")