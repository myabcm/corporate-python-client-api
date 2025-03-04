import json
import os
import time
import uuid
from datetime import datetime

import requests

# --------------------------------------------------------------------------------------
# Constants declaration

OPERATION_SCHEDULED = 0
OPERATION_IN_PROGRESS = 1
OPERATION_ABORTING = 2
OPERATION_FINISHED = 3
OPERATION_ABORTED = 4

SEPARATOR_CONSTANT = "\r\r\r\n\r\r\r"

# --------------------------------------------------------------------------------------
# CorporateServer class

class CorporateServer:
    def __init__(self, base_url, login_name, password, console_feedback=True):
        self.__base_url = base_url
        self.__login_name = login_name
        self.__password = password
        self.__logged_username = ""
        self.__logged_user_id = -1
        self.__session_token = ""
        self.__selected_model_id = -1
        self.__default_idiom_id = 1
        self.__console_feedback = console_feedback

    @staticmethod
    def __status_code_ok(status_code):
        if (status_code >= 200) and (status_code <= 299):
            return True
        else:
            return False

    @staticmethod
    def __get_current_utc_iso8601():
        return datetime.now().isoformat(timespec='milliseconds') + 'Z' #timezone.utc

    def __get_default_headers(self):
        # Set headers with authorization
        headers = {
            "Authorization": f"Bearer {self.__session_token}",
            "Content-Type": "application/json"
        }
        return headers

    def __get_models(self):
        # Set URL
        url = self.__base_url + "/v1/modeling/models"

        # Make GET request
        response = requests.get(url, headers=self.__get_default_headers())

        # Check response
        if CorporateServer.__status_code_ok(response.status_code):
            data = response.json()
            return data
        else:
            raise Exception(f"Error getting models (Status code: {response.status_code})")

    def __get_model_id(self,model_reference):
        # Get models
        models = self.__get_models()

        # Search for desired model (and return its Id if found)
        for model in models:
            if model['Reference'] == model_reference and model['Deleted'] == False:
                return model['Id']

        # Model not found, generate exception
        raise Exception(f"Model {model_reference} not found")

    def __model_exists(self, reference):
        # Get list of available models
        models = self.__get_models()

        # Search for the desired model (and return True if found)
        for model in models:
            if model['Reference'] == reference and model['Deleted'] == False:
                return True

        # Model not found, just return False
        return False

    def __get_export_templates(self):
        # Set URL
        url = self.__base_url + "/v1/base/export-templates"

        # Make GET request
        response = requests.get(url, headers=self.__get_default_headers())

        # Check response
        if CorporateServer.__status_code_ok(response.status_code):
            data = response.json()
            return data
        else:
            raise Exception(f"Error getting export templates (Status code: {response.status_code})")

    def __get_export_template_id(self,export_template_name):
        # Get export templates
        export_templates = self.__get_export_templates()

        # Search for desired model (and return its Id if found)
        for export_template in export_templates:
            if export_template['Name'].upper() == export_template_name.upper():
                return export_template['Id']

        # Model not found, generate exception
        raise Exception(f"Export template {export_template_name} not found")

    def __get_imports(self):
        # Set URL
        url = self.__base_url + "/v1/integration/imports"

        # Make GET request
        response = requests.get(url, headers=self.__get_default_headers())

        # Check response
        if CorporateServer.__status_code_ok(response.status_code):
            # We got a JSON with the import list, just return it
            data = response.json()
            return data
        else:
            raise Exception(f"Error getting imports (Status code: {response.status_code})")

    def __get_import_id(self,import_reference):
        # Get imports
        imports = self.__get_imports()

        # Search for desired import (and return its Id if found)
        for imp in imports:
            if imp['Reference'] == import_reference:
                return imp['Id']

        # Import not found, generate exception
        raise Exception(f"Import {import_reference} not found")

    def __get_exports(self):
        # Set URL
        url = self.__base_url + "/v1/integration/exports"

        # Make GET request
        response = requests.get(url, headers=self.__get_default_headers())

        # Check response
        if CorporateServer.__status_code_ok(response.status_code):
            # We got a JSON with the import list, just return it
            data = response.json()
            return data
        else:
            raise Exception(f"Error getting exports (Status code: {response.status_code})")

    def __get_export_id(self, export_reference):
        # Get exports
        imports = self.__get_exports()

        # Search for desired export (and return its Id if found)
        for imp in imports:
            if imp['Reference'] == export_reference:
                return imp['Id']

        # Export not found, generate exception
        raise Exception(f"Export {export_reference} not found")

    def __get_scripts(self):
        # Set URL
        url = self.__base_url + "/v1/integration/scripts"

        # Make GET request
        response = requests.get(url, headers=self.__get_default_headers())

        # Check response
        if CorporateServer.__status_code_ok(response.status_code):
            # We got a JSON with the import list, just return it
            data = json.loads(response.text)
            return data
        else:
            raise Exception(f"Error getting script (Status code: {response.status_code})")

    def __get_script_id(self, reference):
        # Get scripts
        scripts = self.__get_scripts()

        # Search for desired script (and return its Id if found)
        for scr in scripts:
            if scr['Reference'] == reference:
                return scr['Id']

        # Script not found, generate exception
        raise Exception(f"Script {reference} not found")

    def __get_cubes(self):
        # Set URL
        url = self.__base_url + "/v1/analysis/cubes"

        # Make GET request
        response = requests.get(url, headers=self.__get_default_headers())

        # Check response
        if CorporateServer.__status_code_ok(response.status_code):
            # We got a JSON with the cube list, just return it
            data = json.loads(response.text)
            return data
        else:
            raise Exception(f"Error getting cubes (Status code: {response.status_code})")

    def __get_cube_id(self, reference):
        # Get cubes
        cubes = self.__get_cubes()

        # Search for desired cube (and return its Id if found)
        for cube in cubes:
            if cube['Reference'] == reference:
                return cube['Id']

        # Cube not found, generate exception
        raise Exception(f"Cube {reference} not found")

    def __get_facts(self):
        # Set URL
        url = self.__base_url + "/v1/analysis/facts"

        # Make GET request
        response = requests.get(url, headers=self.__get_default_headers())

        # Check response
        if CorporateServer.__status_code_ok(response.status_code):
            # We got a JSON with the import list, just return it
            data = response.json()
            return data
        else:
            raise Exception(f"Error getting facts (Status code: {response.status_code})")

    def __get_fact_id(self, fact_reference, processable_only=False):
        # Get facts
        facts = self.__get_facts()

        # Search for desired fact (and return its Id if found)
        for fact in facts:
            if fact['Reference'] == fact_reference:
                if fact['FactType'] != 0 and processable_only:
                    raise Exception(f"Fact {fact_reference} was found, but its type is not processable")
                else:
                    return fact['Id']

        # Fact not found, generate exception
        raise Exception(f"Fact {fact_reference} not found")

    def __get_association_list(self, period_scenario_list):
        # Declare our association_list string, iterate over all associations and populate it
        association_list = ""
        for item in period_scenario_list:
            association_id = self.__get_association_id(item.get('PeriodReference'), item.get('ScenarioReference'))
            association_list = association_list + str(association_id) +  ";"

        # Remove the extra ";" at the end of the string
        if association_list.endswith(";"):
            association_list = association_list[:-1]

        return association_list

    def __get_files(self):
        # Set URL & parameters (passing fileType = -1 to get all files)
        url = self.__base_url + "/v1/base/files"
        params = { "fileType": -1 }

        # Make GET request
        response = requests.get(url, headers=self.__get_default_headers(), params=params)

        # Check response
        if CorporateServer.__status_code_ok(response.status_code):
            data = response.json()
            return data
        else:
            raise Exception(f"Error getting files (Status code: {response.status_code})")

    def __get_file_id(self,file_name, username=""):
        # Get files
        files = self.__get_files()

        # Define who we should pick as file's owner (username parameter if passed or current logged user)
        target_user = (username if username != "" else self.__logged_username)

        # Search for desired file (and return its Id if found)
        for file in files:
            if file['FileName'].upper() == file_name.upper() and file['UserName'].upper() == target_user.upper():
                return file['Id']

        # File not found, generate exception
        raise Exception(f"File {file_name} not found for user {target_user}")

    def __store_logged_user_details(self):
        # Set URL
        url = f"{self.__base_url}/v1/base/users/logged/profile"

        # Make GET request
        response = requests.get(url, headers=self.__get_default_headers())

        # Check response
        if CorporateServer.__status_code_ok(response.status_code):
            # Store user details in our class variables
            data = response.json()
            self.__logged_username = data.get("FullName")
            self.__logged_user_id = data.get("Id")
            self.__default_idiom_id = data.get("DefaultIdiomId")
        else:
            # Something got wrong, return exception
            raise Exception(f"Error getting and storing user details (Status code: {response.status_code})")

    def __get_available_associations(self):
        # Set URL & parameters
        url = self.__base_url + "/v1/modeling/models/available-associations"
        params = { "modelid" : self.__selected_model_id }

        # Make GET request
        response = requests.get(url, params=params, headers=self.__get_default_headers())

        # Check response
        if CorporateServer.__status_code_ok(response.status_code):
            # Return JSON with list of available associations
            data = response.json()
            return data
        else:
            # Something got wrong, generate exception with status code
            raise Exception(f"Error model associations (Status code: {response.status_code})")

    def __get_association_id(self, period_reference, scenario_reference):
        # Get available associations
        associations = self.__get_available_associations()

        # Search for desired association (and return its Id if found)
        for association in associations:
            if association['PeriodReference'] == period_reference and association['ScenarioReference'] == scenario_reference:
                return association['Id']

        # Association not found, generate exception
        raise Exception(f"Association {period_reference}/{scenario_reference} not found")

    def __wait_for_operation_to_finish(self, operation_id):
        # Set URL & parameters
        url = f"{self.__base_url}/v1/base/operations/{operation_id}/status"
        params = { "cultureinfo" : "en-US" }

        # Setup helper variables to display our "visual progress indicator"
        signs = ["-", "\\", "|", "/",  "-",  "\\",  "|",  "/"]
        sign_pos = 0

        # Shot our initial  "prograss indicator"
        if self.__console_feedback:
            print("[-]", end="", flush=True)

        # Keep checking every 1 second until operation finishes
        condition = False
        while not condition:
            # Make GET request
            response = requests.get(url, params=params, headers=self.__get_default_headers())

            # Check response
            if CorporateServer.__status_code_ok(response.status_code):
                data = response.json()
                # Check status and return if aborted/finished or wait 1 second and try again
                if data.get("OperationStatus") == OPERATION_ABORTED or data.get("OperationStatus") == OPERATION_FINISHED:
                    condition = True
                else:
                    time.sleep(1)
                    if self.__console_feedback:
                        print(f"\b\b\b[{signs[sign_pos]}]", end="", flush=True)
                        sign_pos = sign_pos + 1 if sign_pos < 7 else 0
            else:
                # Something got wrong, return exception
                raise Exception(f"Error waiting for operation to finish (Status code: {response.status_code})")

        # Overwrite our "progress indicator" with spaces
        if self.__console_feedback:
            print(f"\b\b\b   \b\b\b", end="", flush=True)

    def __get_script_operations_in_group(self, group_id):
        # Set URL & parameters
        url = self.__base_url + "/v1/base/operations/in-group"
        params = { "groupId" : group_id, "pending" : False, "cultureInfo": self.__default_idiom_id }

        # Make GET request
        response = requests.get(url, params=params, headers=self.__get_default_headers())

        # Check response
        if CorporateServer.__status_code_ok(response.status_code):
            # Return JSON with list of scheduled operations
            return response.json()
        else:
            # Something got wrong, generate exception with status code
            raise Exception(f"Error getting pending operations in group {group_id} (Status code: {response.status_code})")

    def __get_session_token(self):
        """Get current session token

            Returns:
            string: session token or empty string
        """
        return self.__session_token

    def logon(self):
        """Logon to MyABCM Corporate using the credentials informed when creating the CorporateServer object

            Returns:
            Nothing if logon is sucessfull or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Logging on to {self.__base_url} using user {self.__login_name}...", end="")

        # Set URL & parameters
        url = self.__base_url + "/v1/base/logon"
        body = {"Username": self.__login_name, "Password": self.__password, "ClientIPAddress": "127.0.0.1" }

        # Make POST request
        response = requests.post(url, json=body)

        # Check response
        if CorporateServer.__status_code_ok(response.status_code):
            data = response.json()
            if data.get("Result") == 0:
                # Login succesfull, store session token
                self.__session_token = data.get("SessionToken")
                # Store additional user details
                self.__store_logged_user_details()

                if self.__console_feedback: print("ok")
            else:
                if self.__console_feedback: print(f"failed")

                # Login failed, generate custom exception based on result code
                if data.get("Result") == 6: # PasswordExpired
                    raise Exception("Error logging in (Password expired)")
                if data.get("Result") == 7: # ProductNotAuthorized
                    raise Exception("Error logging in (Product not authorized)")
                if data.get("Result") == 8: # LicenseNotAvailable
                    raise Exception("Error logging in (License not available)")
                if data.get("Result") == 9: # UserNotAuthorized
                    raise Exception("Error logging in (User not authorized expired)")

                # Result code not in 6 to 9 range, generate generic exception with result code
                raise Exception(f"Error logging in (Logon result code: {data.get('Result')})")
        else:
            # Something got wrong, generate exception with status code
            raise Exception(f"Error logging in (Status code: {response.status_code})")

    def logoff(self):
        """Logoff from MyABCM Corporate

            Returns:
            Nothing if logoff is sucessfull or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Logging off from {self.__base_url} using user {self.__login_name}...", end="")

        # Set URL & parameters
        url = self.__base_url + "/v1/base/logoff"
        body = {"ClientIPAddress": "127.0.0.1"}

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check reponse
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")

            raise Exception(f"Error logging off (Status code: {response.status_code})")
        else:
            if self.__console_feedback: print("ok")

    def select_model(self, reference):
        """Select a model

            Parameters:
            reference (string): Reference of the model to be selected

            Returns:
            Nothing if model is selected or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Selecting model {reference}...", end="")

        # Get model id
        model_id = self.__get_model_id(reference)

        # Set URL & parameters
        url = self.__base_url + "/v1/modeling/models/selected"
        body = {"ModelId": model_id}

        # Make GET request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check response
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("Failed")

            raise Exception(f"Error selecting model (Status code: {response.status_code})")
        else:
            if self.__console_feedback: print("ok")

        self.__selected_model_id = model_id

    def model_exists(self, reference):
        """Check if model exists

            Parameters:
            reference (string): Reference of the model to be searched

            Returns:
            True if the model exists or False if it does not.
        """
        if self.__console_feedback: print(f"Checking if model {reference} exists...", end="")

        result = self.__model_exists(reference)

        if result:
            if self.__console_feedback: print("yes")
            return True
        else:
            if self.__console_feedback: print("no")
            return False

    def add_model(self, name, reference, description, audit_level):
        """Add a new model

            Parameters:
            name (string): Name of the model
            reference (string): Reference of the model
            description (string): Descriptoon of the model
            audit_level (int): Audit level. Possible values are: 0 (for Disabled), 1 (for Basic), 2 (for Intermediate) or (3 for Complete)

            Returns:
            Nothing if model is created or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Adding new model {name} ({reference})...", end="")

        # Set URL & parameters
        url = self.__base_url + "/v1/modeling/models"
        body = { "Name": name, "Reference": reference, "Description": description, "AuditLevel": audit_level, "OwnerId": self.__logged_user_id }

        # Make GET request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check response
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")

            raise Exception(f"Error creating model (Status code: {response.status_code})")
        else:
            if self.__console_feedback: print("ok")

    def remove_model(self, reference):
        """Remove an existing model (this function is synchronous and will wait for the model to be deleted)

            Parameters:
            reference (string): Reference of the model

            Returns:
            Nothing if model is removed or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Removing model {reference} from server...", end="")

        # Get model id
        model_id = self.__get_model_id(reference)

        # Set URL & parameters
        url = self.__base_url + "/v1/modeling/models"
        params = { "ids" : model_id }

        # Make DELETE request
        response = requests.delete(url, params=params, headers=self.__get_default_headers())

        # Check response
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")

            raise Exception(f"Error removing model (Status code: {response.status_code})")

        # Loop and wait for model to be deleted
        condition = True
        while condition:
            condition = self.__model_exists(reference)
            if self.__console_feedback: print(".", end= "")
            time.sleep(1)
            if self.__console_feedback: print("\b", end= "")

        if self.__console_feedback: print("ok")

    def calculate_model(self, period_reference, scenario_reference, notify_by_email):
        """Calculate model (this function is synchronous and will wait for the model to be calculated)
            Parameters:
            period_reference (string): Reference of the period
            scenario_reference (string): Reference of the scenario
            notify_by_email (int): 1 for the user to be notified by email when the calculation ends or 0 for the user not to be notified

            Returns:
            Nothing if model is calculated or an Exception if it fails for any reason
        """
        if self.__console_feedback: print("Calculating currently selected model...", end="")

        # Get association id
        association_id = self.__get_association_id(period_reference, scenario_reference)

        # Set URL & parameters
        url = self.__base_url + "/v1/modeling/models/selected/calculate"
        body = {"PeriodScenarioIds": [association_id],
                "OperationDate":  CorporateServer.__get_current_utc_iso8601(),
                "NotifyByEmail": notify_by_email
                }

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check response
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error starting model calculation (Status code: {response.status_code})")

        # Read operation id (that is returned in response.text)
        operation_id = response.text

        # Wait for operation to finish
        self.__wait_for_operation_to_finish(operation_id)

        if self.__console_feedback: print("ok")

    def file_exists(self, file_name, username=""):
        """Check if file exists in server

            Parameters:
            file_name (string): Complete name of the file to be uploaded
            username (string): Optional parameter indicating the owner of the file

            Returns:
            True if the file exists, otherwise False
        """
        # Get files
        files = self.__get_files()

        # Define who should we pick as file's owner (username parameter if passed or current logged user)
        target_user = (username if username != "" else self.__logged_username)

        # Search for desired file (and return its Id if found)
        for file in files:
            if file['FileName'].upper() == file_name.upper() and file['UserName'].upper() == target_user.upper():
                return True

        return False

    def upload_file(self, file_name, file_type, replace_existing):
        """Upload file to the server

            Parameters:
            file_name (string): Complete name of the local file to be uploaded
            file_type (integer): Type of the file (0 = Excel, 1 = Access, 2 = ETL/X, 3 = CSV)
            replace_existing (integer): 1 for replacing existing file or 0 to not replace it

            Returns:
            Nothing if file is uploaded or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Uploading file {file_name}...", end="")

        # Set URL
        url = self.__base_url + "/v1/base/files"

        # Set header with authorization
        # We don't use the default header used in all ather calls as we do not
        # wnat the default content type "application/json" in this call
        headers = {
            'Authorization': f'Bearer {self.__session_token}'
        }

        # Open local file for reading and call the REST API
        with open(file_name, 'rb') as file:
            # Set file & data
            files =  {
                'file': (file_name, file, 'multipart/form-data')
            }
            data = {
                'chunkMetadata': f"{{\"FileName\": \"{os.path.basename(file_name)}\", \"Index\": 0, \"TotalCount\": 1, \"FileSize\": {str(os.path.getsize(file_name))}, \"FileType\": \"\", \"FileGuid\": \"{str(uuid.uuid4())}\"}}",
                "FileType": file_type,
                "ReplaceExisting": replace_existing,
                "FileStoreUserId": self.__logged_user_id
            }

            # Make POST request
            response = requests.post(url, headers=headers, files=files, data=data)

            # Check response
            if not CorporateServer.__status_code_ok(response.status_code):
                if self.__console_feedback: print("failed")
                raise Exception(f"Error uploading file {file_name} (Status code: {response.status_code}. Text: {response.text})")
            else:
                if self.__console_feedback: print("ok")

    def remove_file(self, file_name):
        """Remove file from server

            WARNING: This function assumes the current logged user is the owner of the
                     file being removed.

            Parameters:
            file_name (string): name of the file to be uploaded

            Returns:
            Nothing if file is removed or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Removing file {file_name} from server...", end="")

        # Get the ID of the file to be removed (assuming here the current logged user is the file ownwer)
        file_id = self.__get_file_id(file_name)

        # Set URL & parameters
        url = self.__base_url + "/v1/base/files"
        params = { "ids": file_id }

        # Make DELETE request
        response = requests.delete(url, headers=self.__get_default_headers(), params=params)

        # Check response
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error removing file {file_name} (Status code: {response.status_code}. Text: {response.text})")
        else:
            if self.__console_feedback: print("ok")

    def import_exists(self, reference):
        """Check if import exists

            Parameters:
            reference (string): Reference of the import

            Returns:
            True if it exists, otherwise False
        """
        if self.__console_feedback: print(f"Checking if import exists {reference}...", end="")
        # Get imports
        imports = self.__get_imports()

        # Search for desired import (and return its Id if found)
        for imp in imports:
            if imp['Reference'] == reference:
                if self.__console_feedback: print("yes")
                return True

        if self.__console_feedback: print("no")
        return False

    def add_import(self, parameters):
        """Add a new import to the selected model

            Parameters:
            parameters: Dictionary with all properties required for the import. For more info, check swagger documentation

            Returns:
            Nothing if operation is sucessfull or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Adding new import to currently selected model...", end="")

        # Make sure we have the minimum required properties in the parameters dictionary
        if parameters.get("Name") is None:
            if self.__console_feedback: print("failed")
            raise Exception("Missing required property 'Name'")
        if parameters.get("Reference") is None:
            if self.__console_feedback: print("failed")
            raise Exception("Missing required property 'Reference'")
        if parameters.get("DataSourceType") is None:
            if self.__console_feedback: print("failed")
            raise Exception("Missing required property 'DataSourceType'")
        if parameters.get("DataSourceParameter") is None:
            if self.__console_feedback: print("failed")
            raise Exception("Missing required property 'DataSourceParameter'")

        # Store DataSourceType and DataSourceParameter in our helper variables
        datasource_type = parameters.get("DataSourceType")
        datasource_parameter = parameters.get("DataSourceParameter")

        # Validate datasource_type
        if datasource_type < 0 or datasource_type > 7:
            raise Exception("Invalid DataSourceType. Must be between 0 and 7")

        # Validate datasource_parameter (based on datasource_type)
        if datasource_type == 0 or datasource_type == 1 or datasource_type == 5:
            # Parameter is and EXCEL, ACCESS or ETL file, so get file it
            if self.file_exists(datasource_parameter):
                datasource_parameter = self.__get_file_id(datasource_parameter)
            else:
                raise Exception(f"File {datasource_parameter} not found in server for the current logged user")

        elif datasource_type == 6:
            # Parameter is a MODEL REFERENCE, so we have to get the model id
            if self.__model_exists(datasource_parameter):
                datasource_parameter = self.__get_model_id(datasource_parameter)
            else:
                raise Exception(f"Model {datasource_parameter} does not exist or it is not currently accessible for the current logged user")

        elif datasource_type == 4:
            # Parameter is a DataMap, datasource parameter is ignored in this
            # case, so we set it to an empty string
            datasource_parameter =  ""

        # If datasource type is 2 (OLE DB), 3 (SQL Server) or 4 (Oracle), we just use the
        # datasource_parameter with no further validation

        # Set URL & parameters(body)
        url = self.__base_url + "/v1/integration/imports"
        body = {
            "Name": parameters.get("Name"),
            "Reference": parameters.get("Reference"),
            "Description": parameters.get("Description") if parameters.get("Description") is not None else "",
            "DataSourceType": datasource_type,
            "DataSourceParameter": str(datasource_parameter),
            "Dimensions": parameters.get("Dimensions") if parameters.get("Dimensions") is not None else "",
            "DimensionMembers": parameters.get("DimensionMembers") if parameters.get("DimensionMembers") is not None else "",
            "Modules": parameters.get("Modules") if parameters.get("Modules") is not None else "",
            "ModuleDimensions": parameters.get("ModuleDimensions") if parameters.get("ModuleDimensions") is not None else "",
            "Members": parameters.get("Members") if parameters.get("Members") is not None else "",
            "DimensionMemberAssociations": parameters.get("DimensionMemberAssociations") if parameters.get("DimensionMemberAssociations") is not None else "",
            "Drivers": parameters.get("Drivers") if parameters.get("Drivers") is not None else "",
            "DriverSteps": parameters.get("DriverSteps") if parameters.get("DriverSteps") is not None else "",
            "Attributes": parameters.get("Attributes") if parameters.get("Attributes") is not None else "",
            "Periods": parameters.get("Periods") if parameters.get("Periods") is not None else "",
            "Scenarios": parameters.get("Scenarios") if parameters.get("Scenarios") is not None else "",
            "Associations": parameters.get("Associations") if parameters.get("Associations") is not None else "",
            "FixedAssignments": parameters.get("FixedAssignments") if parameters.get("FixedAssignments") is not None else "",
            "FixedAttributeInstances": parameters.get("FixedAttributeInstances") if parameters.get("FixedAttributeInstances") is not None else "",
            "MemberInstances": parameters.get("MemberInstances") if parameters.get("MemberInstances") is not None else "",
            "Assignments": parameters.get("Assignments") if parameters.get("Assignments") is not None else "",
            "AttributeInstances": parameters.get("AttributeInstances") if parameters.get("AttributeInstances") is not None else "",
            "SurveyGroups": parameters.get("SurveyGroups") if parameters.get("SurveyGroups") is not None else "",
            "Surveys": parameters.get("Surveys") if parameters.get("Surveys") is not None else "",
            "SurveyDriverMembers": parameters.get("SurveyDriverMembers") if parameters.get("SurveyDriverMembers") is not None else "",
            "SurveyDriverMemberUsers": parameters.get("SurveyDriverMemberUsers") if parameters.get("SurveyDriverMemberUsers") is not None else "",
            "SurveyAttributeMembers": parameters.get("SurveyAttributeMembers") if parameters.get("SurveyAttributeMembers") is not None else "",
            "SurveyAttributeMemberUsers": parameters.get("SurveyAttributeMemberUsers") if parameters.get("SurveyAttributeMemberUsers") is not None else "",
            "KPIGroups": parameters.get("KPIGroups") if parameters.get("KPIGroups") is not None else "",
            "KPIGroupRules": parameters.get("KPIGroupRules") if parameters.get("KPIGroupRules") is not None else "",
            "KPIGroupRuleAlerts": parameters.get("KPIGroupRuleAlerts") if parameters.get("KPIGroupRuleAlerts") is not None else "",
            "KPIs": parameters.get("KPIs") if parameters.get("KPIs") is not None else "",
            "KPIRules": parameters.get("KPIRules") if parameters.get("KPIRules") is not None else "",
            "KPIRuleAlerts": parameters.get("KPIRuleAlerts") if parameters.get("KPIRuleAlerts") is not None else "",
            "KPIAlerts": parameters.get("KPIAlerts") if parameters.get("KPIAlerts") is not None else "",
            "KPIGroupInstances": parameters.get("KPIGroupInstances") if parameters.get("KPIGroupInstances") is not None else "",
            "KPIInstances": parameters.get("KPIInstances") if parameters.get("KPIInstances") is not None else "",
            "MemberACLs": parameters.get("MemberACLs") if parameters.get("MemberACLs") is not None else "",
            "AdditionalTables": parameters.get("AdditionalTables") if parameters.get("AdditionalTables") is not None else False,
            "DataReaderMode": parameters.get("DataReaderMode") if parameters.get("DataReaderMode") is not None else 1,
            "GuessingLinesCount": parameters.get("GuessingLinesCount") if parameters.get("GuessingLinesCount") is not None else 0,
            "TreatGuessedIntColumnsAsDouble": parameters.get("TreatGuessedIntColumnsAsDouble") if parameters.get("TreatGuessedIntColumnsAsDouble") is not None else True
        }

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check response
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error adding import {parameters.get("Name")} (Status code: {response.status_code}. Text: {response.text})")
        else:
            if self.__console_feedback: print("ok")

    def execute_import(self, reference, idiom_id=-1):
        """Execute import (this function is synchronous and will wait for the imported to finish executing)

        Parameters:
        reference (string): Reference of the import
        idiom_id (int): Id of the idiom to be used

        Returns:
        Nothing if import is executed or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Execute import {reference}...", end="")

        # Get import id
        import_id = self.__get_import_id(reference)

        # Set URL & parameters
        url = f"{self.__base_url}/v1/integration/imports/{import_id}/execute"
        body = {"OperationDate":  CorporateServer.__get_current_utc_iso8601(),
                "NotifyByEmail": True,
                "IdiomId": idiom_id if idiom_id != -1 else self.__default_idiom_id,
                "UseTransaction": True}

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error calling execute import (Status code: {response.status_code})")

        # Read operation id (that is returned in response.text)
        operation_id =  response.text

        # Wait for operation to finish
        self.__wait_for_operation_to_finish(operation_id)

        if self.__console_feedback: print("ok");

    def remove_import(self, reference):
        """Remove an existing import

            Parameters:
            reference (string): Reference of the import

            Returns:
            Nothing if import is removed or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Remove import {reference}...", end="")

        # Get import id
        import_id = self.__get_import_id(reference)

        # Set URL
        url = self.__base_url + f"/v1/integration/imports/{import_id}"

        # Make DELETE request
        response = requests.delete(url, headers=self.__get_default_headers())

        # Check response
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed");
            raise Exception(f"Error removing import (Status code: {response.status_code})")
        else:
            if self.__console_feedback: print("ok");

    def add_script(self, name, reference, description):
        """Add a new script

            Parameters:
            name (string): Name of the script
            reference (string): Reference of the script
            description (string): Descriptoon of the script

            Returns:
            Nothing if script is created or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Adding new script {name} ({reference})...", end="")

        # Set URL & parameters
        url = self.__base_url + "/v1/integration/scripts"
        body = { "Name": name, "Reference": reference, "Description": description }

        # Make GET request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check response
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")

            raise Exception(f"Error creating script (Status code: {response.status_code})")
        else:
            if self.__console_feedback: print("ok")

    def remove_script(self, reference):
        """Remove an existing script

            Parameters:
            reference (string): Reference of the script

            Returns:
            Nothing if script is removed or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Removing script {reference} from model...", end="")

        # Get script id
        script_id = self.__get_script_id(reference)

        # Set URL & parameters
        url = self.__base_url + "/v1/integration/scripts"
        params = { "ids" : script_id }

        # Make DELETE request
        response = requests.delete(url, params=params, headers=self.__get_default_headers())

        # Check response
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")

            raise Exception(f"Error removing script (Status code: {response.status_code})")
        else:
            if self.__console_feedback: print("ok")

    def add_md_cube_to_script(self, script_reference, cube_reference, force_reprocessing):
        """Add multidimensional cube to script

            Parameters:
            script_reference (string): Reference of the script where the cube will be added
            cube_reference (string): Reference of the cube to be added
            force_reprocessing (boolean): Indicates if the cube has to be completely reprocessing

            Returns:
            Nothing if cube is added an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Adding multidimensional cube {cube_reference} to script {script_reference}...", end="")

        # Get script id
        script_id = self.__get_script_id(script_reference)

        # Get cube id
        cube_id = self.__get_cube_id(cube_reference)

        # Set URL & parameters
        url = f"{self.__base_url}/v1/integration/scripts/{script_id}/operations"
        # OperationId, Name, OperationOrd and AccessRight properties are not used by the server and are set to 0 or empty string here
        body = { "Operations": [ { "OperationId": 0, "OperationType": 1, "Details": f"C={{{str(cube_id)}}} F={{{force_reprocessing}}}", "Name":  "", "OperationOrd": 0, "AccessRight": 0 } ] }

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
             if self.__console_feedback: print("failed")
             raise Exception(f"Error adding cube to script (Status code: {response.status_code})")
        else:
            if self.__console_feedback: print("ok")

    def add_tb_cube_to_script(self, script_reference, cube_reference, processing_type, period_scenario_list=None):
        """Add tabular cube to script

            Parameters:
            script_reference (string): Reference of the script where the cube will be added
            cube_reference (string): Reference of the cube to be added
            processing_type (int): How to reprocess the cube. Use:
                                    0: Add new cube facts only
                                    1: Reprocess current cube facts only
                                    2: Reprocess current cube facts and its dimensions
                                    3: Reprocess current cube facts, its dimensions and related cubes
            period_scenario_list (list) : List of period_reference/scenario_reference to be processed

            Returns:
            Nothing if cube is added an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Adding tabular cube {cube_reference} to script {script_reference}...", end="")

        # Get script id
        script_id = self.__get_script_id(script_reference)

        # Get cube id
        cube_id = self.__get_cube_id(cube_reference)

        # Convert period/scenario list into an association id string separated by commo
        ps_ids = self.__get_association_list(period_scenario_list)

        # Set URL & parameters
        url = f"{self.__base_url}/v1/integration/scripts/{script_id}/operations"
        # OperationId, Name, OperationOrd and AccessRight properties are not used by the server and are set to 0 or empty string here
        body = { "Operations": [ { "OperationId": 0, "OperationType": 1, "Details": f"C={{{str(cube_id)}}} T={{{processing_type}}} A={{{ps_ids}}}", "Name":  "", "OperationOrd": 0, "AccessRight": 0 } ] }

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error adding cube to script (Status code: {response.status_code})")
        else:
            if self.__console_feedback: print("ok")

    def add_export_to_script(self, script_reference, export_reference):
        """Add export cube to script

            Parameters:
            script_reference (string): Reference of the script where the cube will be added
            export_reference (string): Reference of the export to be added

            Returns:
            Nothing if export is added an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Adding export {export_reference} to script {script_reference}...", end="")

        # Get script id
        script_id = self.__get_script_id(script_reference)

        # Get export id
        export_id = self.__get_export_id(export_reference)

        # Set URL & parameters
        url = f"{self.__base_url}/v1/integration/scripts/{script_id}/operations"
        # OperationId, Name, OperationOrd and AccessRight properties are not used by the server and are set to 0 or empty string here
        body = { "Operations": [ { "OperationId": 0, "OperationType": 5, "Details": str(export_id), "Name":  "", "OperationOrd": 0, "AccessRight": 0 } ] }

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error adding export to script (Status code: {response.status_code})")
        else:
            if self.__console_feedback: print("ok")

    def add_import_to_script(self, script_reference, import_reference):
        """Add impport cube to script

            Parameters:
            script_reference (string): Reference of the script where the cube will be added
            import_reference (string): Reference of the import to be added

            Returns:
            Nothing if import is added an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Adding import {import_reference} to script {script_reference}...", end="")

        # Get script id
        script_id = self.__get_script_id(script_reference)

        # Get import id
        import_id = self.__get_import_id(import_reference)

        # Set URL & parameters
        url = f"{self.__base_url}/v1/integration/scripts/{script_id}/operations"
        # OperationId, Name, OperationOrd and AccessRight properties are not used by the server and are set to 0 or empty string here
        body = { "Operations": [ { "OperationId": 0, "OperationType": 2, "Details": str(import_id), "Name":  "", "OperationOrd": 0, "AccessRight": 0 } ] }

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error adding import to script (Status code: {response.status_code})")
        else:
            if self.__console_feedback: print("ok")

    def add_model_calculation_to_script(self, script_reference, period_scenario_list):
        """Add calculation operation to script

        Parameters:
        script_reference (string): Reference of the script where the cube will be added
        period_scenario_list (list): List of period/scenario references

        Returns:
        Nothing if calculation is added an Exception if it fails for any reason
        """

        if self.__console_feedback: print(f"Adding calculation to script...", end="")

        # Get script id
        script_id = self.__get_script_id(script_reference)

        # Convert period/scenario list into an association id string separated by commo
        ps_ids = self.__get_association_list(period_scenario_list)

        # Set URL & parameters
        url = f"{self.__base_url}/v1/integration/scripts/{script_id}/operations"
        # OperationId, Name, OperationOrd and AccessRight properties are not used by the server and are set to 0 or empty string here
        body = { "Operations": [ { "OperationId": 0, "OperationType": 0, "Details": ps_ids, "Name":  "", "OperationOrd": 0, "AccessRight": 0 } ] }

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error adding calculation to script (Status code: {response.status_code})")
        else:
            if self.__console_feedback: print("ok")

    def add_etlx_file_to_script(self, script_reference, etlx_filename):
        """Add ETLX file processing to script

            Parameters:
            script_reference (string): Reference of the script where the cube will be added
            etlx_filename (string): Name of the ETLX file

            Returns:
            Nothing if ETLX file is added an Exception if it fails for any reason
            """

        if self.__console_feedback: print(f"Adding ETLX file {etlx_filename} to script {script_reference}...", end="")

        # Get script id
        script_id = self.__get_script_id(script_reference)

        # Get file id
        file_id = self.__get_file_id(etlx_filename)

        # Set URL & parameters
        url = f"{self.__base_url}/v1/integration/scripts/{script_id}/operations"
        details =  "1" + SEPARATOR_CONSTANT + str(file_id) + SEPARATOR_CONSTANT + "" + SEPARATOR_CONSTANT +  "" + SEPARATOR_CONSTANT +  "False" + SEPARATOR_CONSTANT +  "" + SEPARATOR_CONSTANT +  "" + SEPARATOR_CONSTANT

        # OperationId, Name, OperationOrd and AccessRight properties are not used by the server and are set to 0 or empty string here
        body = { "Operations": [ { "OperationId": 0, "OperationType": 15, "Details": details, "Name":  "", "OperationOrd": 0, "AccessRight": 0 } ] }

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error ETLX file to script (Status code: {response.status_code})")
        else:
            if self.__console_feedback: print("ok")

    def add_etlx_database_to_script(self, script_reference, server, database, integrated_security, username, password):
        """Add ETLX database processing to script

            Parameters:
            script_reference (string): Reference of the script where the cube will be added
            server (string): Server name
            database (string): Database name
            integrated_security (boolean): True for using integrated security, otherwise False
            username (string): Username
            password (string): Password

            Returns:
            Nothing if ETLX database is added an Exception if it fails for any reason
        """

        if self.__console_feedback: print(f"Adding ETLX database {database} to script {script_reference}...", end="")

        # Get script id
        script_id = self.__get_script_id(script_reference)

        # Set URL & parameters
        url = f"{self.__base_url}/v1/integration/scripts/{script_id}/operations"
        details =  "2" + SEPARATOR_CONSTANT +  "0" + SEPARATOR_CONSTANT + server + SEPARATOR_CONSTANT +  database + SEPARATOR_CONSTANT +  str(integrated_security) + SEPARATOR_CONSTANT +  username + SEPARATOR_CONSTANT +  password + SEPARATOR_CONSTANT

        # OperationId, Name, OperationOrd and AccessRight properties are not used by the server and are set to 0 or empty string here
        body = { "Operations": [ { "OperationId": 0, "OperationType": 15, "Details": details, "Name":  "", "OperationOrd": 0, "AccessRight": 0 } ] }

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error ETLX database to script (Status code: {response.status_code})")
        else:
            if self.__console_feedback: print("ok")

    def add_fact_to_script(self, script_reference, fact_reference):
        """Add fact to script

        Parameters:
        script_reference (string): Reference of the script where the cube will be added
        fact_reference (string): Reference  of the fact

        Returns:
        Nothing if fact is added an Exception if it fails for any reason
        """

        if self.__console_feedback: print(f"Adding fact {fact_reference} to script {script_reference}...", end="")

        # Get script id
        script_id = self.__get_script_id(script_reference)

        # Get fact id
        fact_id = self.__get_fact_id(fact_reference, True)

        # Set URL & parameters
        url = f"{self.__base_url}/v1/integration/scripts/{script_id}/operations"

        # OperationId, Name, OperationOrd and AccessRight properties are not used by the server and are set to 0 or empty string here
        body = { "Operations": [ { "OperationId": 0, "OperationType": 9, "Details": str(fact_id), "Name":  "", "OperationOrd": 0, "AccessRight": 0 } ] }

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error adding fact to script (Status code: {response.status_code})")
        else:
            if self.__console_feedback: print("ok")

    def execute_script(self, reference, idiom_id=-1):
        """Execute script (this function is executed synchronously ONLY if the script has 1 or more
           operations that are not exports. If all operations in the script are exports, it will
           execute asynchronously)

            Parameters:
            reference (string): Reference of the script
            idiom_id (int): Id of the idiom to be used

            Returns:
            Nothing if script starts execution or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Start script {reference}...", end="")

        # Get script id
        script_id = self.__get_script_id(reference)

        # Set URL & parameters
        url = f"{self.__base_url}/v1/integration/scripts/{script_id}/execute"
        body = {
            "DefaultAssociationId": -1,
            "ScriptParameters": [],
            "OperationDate": CorporateServer.__get_current_utc_iso8601(),
            "NotifyByEmail": True,
            "IdiomId": idiom_id if idiom_id != -1 else self.__default_idiom_id}

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error starting script (Status code: {response.status_code})")

        # Get group id from the response
        group_id = response.text

        # If we do not have a group id in the response, just return without waiting
        if group_id == -1:
            if self.__console_feedback: print("ok (script had only exports, cannot wait for execution synchronously)");
            return

        # Setup helper variables to display our "visual progress indicator"
        signs = ["-", "\\", "|", "/",  "-",  "\\",  "|",  "/"]
        sign_pos = 0

        # Wait until all operations in script are executed
        condition = False
        while not condition:
            operations = self.__get_script_operations_in_group(group_id)

            count = len([op for op in operations if 0 <= op.get('OperationStatus') <= 2])

            if count <= 0:
                condition = True
            else:
                time.sleep(2)
                if self.__console_feedback:
                    print(f"\rStart script {reference}...(remaining {count}) [{signs[sign_pos]}]\033[K", end="", flush=True)
                    sign_pos = sign_pos + 1 if sign_pos < 7 else 0

        if self.__console_feedback: print(f"\rStart script {reference}...ok\033[K")

    def add_fact_associations(self, fact_reference, period_scenario_list):
        """Add fact associations

            Parameters:
            fact_reference (string): Reference of the fact where the associations will be added
            period_scenario_list (list): List of period/scenario references

            Returns:
            Nothing if associations are added or an Exception if it fails for any reason
         """

        if self.__console_feedback: print(f"Adding association(s) to fact {fact_reference}...", end="")

        # Get fact id
        fact_id = self.__get_fact_id(fact_reference)

        # Convert period/scenario list into an association id string separated by comma
        ps_ids = self.__get_association_list(period_scenario_list)

        # Convert ps_ids to a list if integers with the ps_ids
        ps_ids_int_list = list(map(int, ps_ids.split(";")))

        # Set URL & parameters
        url = f"{self.__base_url}/v1/analysis/facts/{fact_id}/associations"
        body = {"AssociationIds": ps_ids_int_list}

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error adding associations to false (Status code: {response.status_code})")
        else:
            if self.__console_feedback: print("ok")

    def remove_fact_associations(self, fact_reference, period_scenario_list):
        """Remove fact associations

            Parameters:
            fact_reference (string): Reference of the fact from where the associations will be removed
            period_scenario_list (list): List of period/scenario references

            Returns:
            Nothing if associations are removed or an Exception if it fails for any reason
        """

        if self.__console_feedback: print(f"Removing association(s) from fact {fact_reference}...", end="")

        # Get fact id
        fact_id = self.__get_fact_id(fact_reference)

        # Convert period/scenario list into an association id string separated by comma
        ps_ids = self.__get_association_list(period_scenario_list)

        # Convert ps_ids to a list if integers with the ps_ids
        ps_ids_int_list = list(map(int, ps_ids.split(";")))

        # Set URL & parameters
        url = f"{self.__base_url}/v1/analysis/facts/{fact_id}/associations"
        body = {"AssociationIds": ps_ids_int_list}

        # Make DELETE request
        response = requests.delete(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error removing associations to false (Status code: {response.status_code})")
        else:
            if self.__console_feedback: print("ok")

    def process_fact_associations(self, fact_reference, period_scenario_list):
        """Execute (process) fact associations

            WARNING: This method executes ASYNCHRONOUSLY and won't wait for the fact association
                    to finish processing

            Parameters:
            fact_reference (string): Reference of the fact
            period_scenario_list (list): List of period/scenario to be processed

            Returns:
            Nothing if fact associations start processing or an Exception if it fails for any reason
        """

        if self.__console_feedback: print(f"Processing association(s) from fact {fact_reference}...", end="")

        # Get fact id
        fact_id = self.__get_fact_id(fact_reference)

        # Convert period/scenario list into an association id string separated by comma
        ps_ids = self.__get_association_list(period_scenario_list)

        # Convert ps_ids to a list if integers with the ps_ids
        ps_ids_int_list = list(map(int, ps_ids.split(";")))

        # Set URL & parameters
        url = f"{self.__base_url}/v1/analysis/facts/{fact_id}/associations/execute"
        body = { "AssociationIds": ps_ids_int_list,
                "OperationDate": self.__get_current_utc_iso8601(),
                "NotifyByEmail": False,
                "GroupIds": [],
                "UserIds": []
            }

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error starting fact association processing (Status code: {response.status_code})")
        else:
            if self.__console_feedback: print("ok")


    def process_fact(self, fact_reference):
        """Process fact (this function is synchronous and will wait for the fact to be procesed)

            Parameters:
            fact_reference (string): Reference of the factr

            Returns:
            Nothing if fact is processed or an Exception if it fails for any reason
                    """
        if self.__console_feedback: print(f"Procesing fact {fact_reference}...", end="")

        # Get fact id
        fact_id = self.__get_fact_id(fact_reference)

        # Set URL & parameters
        url = f"{self.__base_url}/v1/analysis/facts/{fact_id}/execute"
        body = {"OperationDate": CorporateServer.__get_current_utc_iso8601(),
                "NotifyByEmail": False,
                "GroupIds": [],
                "UserIds": []
            }

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error calling process fact (Status code: {response.status_code})")

        # Read operation id (that is returned in response.text)
        operation_id =  response.text

        # Wait for operation to finish
        self.__wait_for_operation_to_finish(operation_id)

        if self.__console_feedback: print("ok");

    def process_regular_cube(self, reference, force_reprocessing):
        """Process cube (this function is synchronous and will wait for the fact to be procesed)

            Parameters:
            reference (string): Reference of the cube

            Returns:
            Nothing if cube is processed or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Procesing cube {reference}...", end="")

        # Get cube id
        cube_id = self.__get_cube_id(reference)

        # Set URL & parameters
        url = f"{self.__base_url}/v1/analysis/cubes/{cube_id}/regular/execute"
        body = {"ForceReprocessing": force_reprocessing,
                "OperationDate": CorporateServer.__get_current_utc_iso8601(),
                "NotifyByEmail": False
                }

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error processing cube (Status code: {response.status_code})")

        # Read operation id (that is returned in response.text)
        operation_id =  response.text

        # Wait for operation to finish
        self.__wait_for_operation_to_finish(operation_id)

        if self.__console_feedback: print("ok");

    def process_tabular_cube(self, reference, cube_processing_type, period_scenario_list):
        """Process cube (this function is synchronous and will wait for the fact to be procesed)

            Parameters:
            reference (string): Reference of the cube
            cube_processing_type (int): Type of processing to do. Valid numbers are:
                                        0: Add new facts only
                                        1: Reprocess current selected facts
                                        2: Reprocess facts and dimensions of current cube only
                                        3: Reprocess facts and dimensions of current cube and affected cubes
            period_scenario_list (list): List of period/scenarios to reprocess

            Returns:
            Nothing if cube is processed or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Procesing cube {reference}...", end="")

        # Get cube id
        cube_id = self.__get_cube_id(reference)

        # Convert period/scenario list into an association id string separated by comma
        ps_ids = self.__get_association_list(period_scenario_list)

        # Convert ps_ids to a list if integers with the ps_ids
        ps_ids_int_list = [] if ps_ids == "" else list(map(int, ps_ids.split(";")))

        # Set URL & parameters
        url = f"{self.__base_url}/v1/analysis/cubes/{cube_id}/tabular/execute"
        body = {
            "CubeProcessingType": cube_processing_type,
            "AssociationIds": ps_ids_int_list,
            "OperationDate":  CorporateServer.__get_current_utc_iso8601(),
            "NotifyByEmail": False
            }

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error processing cube (Status code: {response.status_code})")

        # Read operation id (that is returned in response.text)
        operation_id =  response.text

        # Wait for operation to finish
        self.__wait_for_operation_to_finish(operation_id)

        if self.__console_feedback: print("ok");

    def reset_association(self, period_reference, scenario_reference, parameters=None):
        """Reset association

            Parameters:
            period_reference (string): Period reference
            scenario_reference (string): Scenario reference
            parameters (json): JSON with all parameters

            Returns:
            Nothing if association is reset or an Exception if it fails for any reason
        """
        if parameters is None:
            parameters = {}

        if self.__console_feedback: print(f"Resetting association {period_reference}/{scenario_reference}...", end="")

        # Get assoication id
        ps_id = self.__get_association_id(period_reference, scenario_reference)

        # Set URL & parameters
        url = f"{self.__base_url}/v1/modeling/models/selected/structure/associations/{ps_id}/reset"
        body = {"RemoveAssignments": parameters.get("RemoveAssignments") if parameters.get("RemoveAssignments") is not None else True,
                "RemoveTextAttributeInstances": parameters.get("RemoveTextAttributeInstances") if parameters.get("RemoveTextAttributeInstances") is not None else True,
                "RemoveNumericAttributeInstances": parameters.get("RemoveNumericAttributeInstances") if parameters.get("RemoveNumericAttributeInstances") is not None else True,
                "ResetNumericAttributeQuantities": parameters.get("ResetNumericAttributeQuantities") if parameters.get("ResetNumericAttributeQuantities") is not None else True,
                "ResetDriverQuantitiesAndWeight": parameters.get("ResetDriverQuantitiesAndWeight") if parameters.get("ResetDriverQuantitiesAndWeight") is not None else True,
                "ResetEnteredCosts": parameters.get("ResetEnteredCosts") if parameters.get("ResetEnteredCosts") is not None else True,
                "ResetRevenues": parameters.get("ResetRevenues") if parameters.get("ResetRevenues") is not None else True,
                "ResetOutputQuantities": parameters.get("ResetOutputQuantities") if parameters.get("ResetOutputQuantities") is not None else True,
                "ResetTotalDriverQuantities": parameters.get("ResetTotalDriverQuantities") if parameters.get("ResetTotalDriverQuantities") is not None else True,
                "ResetDefinedCapacities": parameters.get("ResetDefinedCapacities") if parameters.get("ResetDefinedCapacities") is not None else True
                }

        # Make PUT request
        response = requests.put(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error resetting association (Status code: {response.status_code})")
        else:
            if self.__console_feedback: print("ok")

    def remove_cubes_from_olap_server(self):
        """Remove all tabular and multidimensional cubes from OLAP server

            Returns:
            Nothing if cubes are removed or an Exception if it fails for any reason
        """
        if self.__console_feedback: print("Removing cubes from OLAP server...", end="")

        # Set URL
        url = self.__base_url + "/v1/analysis/cubes/olap-server"

        # Make DELETE request
        response = requests.delete(url, headers=self.__get_default_headers())

        # Check response
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")

            raise Exception(f"Error removing cubes from OLAP server (Status code: {response.status_code})")
        else:
            if self.__console_feedback: print("ok")

    def add_export(self, parameters):
        """Add a new export to the selected model

            Parameters:
            parameters: Dictionary with all properties required for the import. For more info, check swagger documentation

            Returns:
            Nothing if operation is sucessfull or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Adding new export to currently selected model...", end="")

        # Make sure we have the minimum required properties in the parameters dictionary
        if parameters.get("Name") is None:
            if self.__console_feedback: print("failed")
            raise Exception("Missing required property 'Name'")
        if parameters.get("Reference") is None:
            if self.__console_feedback: print("failed")
            raise Exception("Missing required property 'Reference'")
        if parameters.get("DataSourceType") is None:
            if self.__console_feedback: print("failed")
            raise Exception("Missing required property 'DataSourceType'")
        if parameters.get("DataSourceParameter") is None:
            if self.__console_feedback: print("failed")
            raise Exception("Missing required property 'DataSourceParameter'")
        if parameters.get("TableName") is None:
            if self.__console_feedback: print("failed")
            raise Exception("Missing required property 'TableName'")

        # Get the export template id (if ExportTemplateName is informed)
        export_template_id = self.__get_export_template_id(parameters.get("ExportTemplateName")) if parameters.get("ExportTemplateName") is not None else 0

        # Store DataSourceType and DataSourceParameter in our helper variables
        datasource_type = parameters.get("DataSourceType")
        datasource_parameter = parameters.get("DataSourceParameter")

        # Validate datasource_type
        if datasource_type < 0 or datasource_type > 7:
            raise Exception("Invalid DataSourceType. Must be between 0 and 7")

        # Validate datasource_parameter (based on datasource_type)
        if datasource_type == 0 or datasource_type == 1 or datasource_type == 5:
            # Parameter is and EXCEL, ACCESS or ETL file, so get file it
            if self.file_exists(datasource_parameter):
                datasource_parameter = self.__get_file_id(datasource_parameter)
            else:
                raise Exception(f"File {datasource_parameter} not found in server for the current logged user")

        elif datasource_type == 6:
            # Parameter is a MODEL REFERENCE, so we have to get the model id
            if self.__model_exists(datasource_parameter):
                datasource_parameter = self.__get_model_id(datasource_parameter)
            else:
                raise Exception(f"Model {datasource_parameter} does not exist or it is not currently accessible for the current logged user")

        elif datasource_type == 4:
            # Parameter is a DataMap, datasource parameter is ignored in this
            # case, so we set it to an empty string
            datasource_parameter =  ""

        # If datasource type is 2 (OLE DB), 3 (SQL Server) or 4 (Oracle), we just use the
        # datasource_parameter with no further validation

        # Set URL & parameters(body)
        url = self.__base_url + "/v1/integration/exports"
        body = {
            "Name": parameters.get("Name"),
            "Reference": parameters.get("Reference"),
            "Description": parameters.get("Description") if parameters.get("Description") is not None else "",
            "DataSourceType": datasource_type,
            "DataSourceParameter": str(datasource_parameter),
            "TableName": parameters.get("TableName") if parameters.get("TableName") is not None else "",
            "Query": parameters.get("Query") if parameters.get("Query") is not None else "",
            "ExportTemplateId": export_template_id,
            "ReplaceData": parameters.get("ReplaceData") if parameters.get("ReplaceData") is not None else True,
        }

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check response
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error adding export {parameters.get("Name")} (Status code: {response.status_code}. Text: {response.text})")
        else:
            if self.__console_feedback: print("ok")

    def remove_export(self, reference):
        """Remove an existing export

            Parameters:
            reference (string): Reference of the export

            Returns:
            Nothing if export is removed or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Removing export {reference}...", end="")

        # Get export id
        export_id = self.__get_export_id(reference)

        # Set URL
        url = self.__base_url + f"/v1/integration/exports/{export_id}"

        # Make DELETE request
        response = requests.delete(url, headers=self.__get_default_headers())

        # Check response
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed");
            raise Exception(f"Error removing export (Status code: {response.status_code})")
        else:
            if self.__console_feedback: print("ok");

    def execute_export(self, reference, parameters=None, idiom_id=-1):
        """Execute export (this function is synchronous and will wait for the export to finish executing)

            Parameters:
            reference (string): Reference of the export
            idiom_id (int): Id of the idiom to be used

            Returns:
            Nothing if export is executed or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Executing export {reference}...", end="")

        # Get export id
        export_id = self.__get_export_id(reference)

        # Set parameters' values (if informed)
        parameter_values = parameters if parameters is not None else []

        # Set URL & parameters
        url = f"{self.__base_url}/v1/integration/exports/{export_id}/execute"
        body = {"ParametersValue": parameter_values,
                "OperationDate":  CorporateServer.__get_current_utc_iso8601(),
                "NotifyByEmail": True,
                "IdiomId": idiom_id if idiom_id != -1 else self.__default_idiom_id}

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error calling execute export (Status code: {response.status_code})")

        # Read operation id (that is returned in response.text)
        operation_id =  response.text

        # Wait for operation to finish
        self.__wait_for_operation_to_finish(operation_id)

        if self.__console_feedback: print("ok");