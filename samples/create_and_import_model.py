import os
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

try:
    # Read credentials from disk (credentials.json)
    with open('credentials.json', 'r', encoding='utf-8') as file:
        credentials = json.load(file)

    # declare help variables
    etlx_full_filename = "D:/dev/corporate-python-client-api/samples/demo_model.etlx"
    etlx_filename_only = os.path.basename(etlx_full_filename)

    model_name        = "My Sample Model (test)"
    model_reference   = "MDL-SAMPLE"
    model_description = "My Sample Model description (test)"

    # create corporate server object and logon
    corporate_server = CorporateServer(credentials.get("server"), credentials.get("username"), credentials.get("password"))
    corporate_server.logon()

    # check if etlxfile alsready exis in file store and upload it again if needed
    if corporate_server.file_exists(etlx_filename_only):
        user_input = input(f"File {etlx_filename_only} already exists. Do you want to replace it (y/n)?").strip().lower()

        if user_input == "y":
            print(f"Current file {etlx_filename_only} will be removed and uploaded again")
            corporate_server.remove_file(etlx_filename_only)
            corporate_server.upload_file(etlx_full_filename, 2, True)

        elif  user_input == "n":
            print(f"Current file {etlx_filename_only} will be used")

        else:
            print("Invalid response. You must type y or n. Cancelling script")
            quit()

    # check if model exists and if so, check if user really wants to proceed by replacing it
    if corporate_server.model_exists(model_reference):
        user_input = input(f"Model {model_reference} already exists. Do you want to replace it (y/n)?").strip().lower()

        if user_input == "y":
            print(f"Current model {model_reference} will be removed and recreated")
            corporate_server.remove_model(model_reference)

        elif  user_input == "n":
            print(f"Cancelling script")
            quit()

        else:
            print("Invalid response. You must type y or n. Cancelling script")
            quit()

    # create new model
    corporate_server.add_model(model_name,  model_reference, model_description, 0)

    # select new model
    corporate_server.select_model(model_reference)

    # create a new import
    corporate_server.add_import({
        "Name": "Import All",
        "Reference": "IMP-IA",
        "Description": "Import All description",
        "DataSourceType": 5, # ETLX
        "DataSourceParameter": etlx_filename_only,
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
        "AdditionalTables": True
    })

    # execute the import
    corporate_server.execute_import("IMP-IA")

    # execute the script  "Script01" that should have been imported with the model
    corporate_server.execute_script("Script01")

    # remove the import (as it is not necessary anymore)
    corporate_server.remove_import("IMP-IA")

    # logoff from server
    corporate_server.logoff()

except Exception as e:
    print(f"\n\nSCRIPT ERROR: {e}")