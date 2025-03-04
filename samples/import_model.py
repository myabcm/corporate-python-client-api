import os
import sys
import json
#from myabcm_corporate_client_api import CorporateServer

# --------------------------------------------------------------------------------------
# This sample uses the myabcm_corporate_client_api package from Python Package index.
# If you want to use the source code of the package direcly for debugging/improving it,
# COMMENT the line above importing CorporateSever from myabcm_corporate_client_api
# and UNCOMMENT the 5 lines below
# --------------------------------------------------------------------------------------
import platform
module_dir = os.path.abspath("../src/myabcm_corporate_client_api")
if module_dir not in sys.path:
    sys.path.append(module_dir)
from corporate_server_module import CorporateServer

# Variables used in the script
file_path =  f"{os.path.abspath("./")}\\"
file_name = "demo_model.etlx"
file_type = 2

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

    # Upload file to server (if it is not already there)
    if not corporate_server.file_exists(file_name):
        corporate_server.upload_file(file_path + file_name, file_type, True)

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

    # Select the new model
    corporate_server.select_model(model_reference)

    # Add a new import
    corporate_server.add_import({
        "Name": "Import All",
        "Reference": "IMP-IA",
        "Description": "Import All description",
        "DataSourceType": 5, # ETLX
        "DataSourceParameter": "demo_model.etlx",
        "Dimensions": "CIMP_DIMENSIONS",
        "DimensionMembers": "CIMP_DIM_MEMBERS",
        "Modules": "CIMP_MODULES",
        "ModuleDimensions": "CIMP_MODULE_DIMENSIONS",
        "Members": "CIMP_MEMBERS",
        "DimensionMemberAssociations": "CIMP_DIM_MEMBERS_ASSOCIATION",
        "Drivers": "CIMP_DRIVERS",
        "Attributes": "CIMP_ATTRIBUTES",
        "Periods": "CIMP_PERIODS",
        "Scenarios": "CIMP_SCENARIOS",
        "Associations": "CIMP_ASSOCIATIONS",
        "FixedAssignments": "CIMP_STRUCT_MEMBER_ASSIGNMENTS",
        "FixedAttributeInstances": "CIMP_STRUCT_MEMBER_ATTRIBUTES",
        "MemberInstances": "CIMP_MEMBER_INSTANCES",
        "Assignments": "CIMP_MEMBER_INST_ASSIGNMENTS",
        "AttributeInstances": "CIMP_MEMBER_INST_ATTRIBUTES",
        "AdditionalTables": True})

    # Execute import
    corporate_server.execute_import("IMP-IA")

    # Remove import just created and executed
    corporate_server.remove_import("IMP-IA")

    # Logoff from server
    corporate_server.logoff()

except Exception as e:
    print(f"\n\nSCRIPT ERROR: {e}")
