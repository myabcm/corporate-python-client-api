import json
import os
import time
import uuid
from datetime import datetime
from typing import List, Dict

from .enums import AbmFactType, LogonResult, AbmDataSourceType, AbmEtlType, AbmOperationType, AbmOperationStatus
from .error_handler import get_error_message_from_response
import requests
from requests.exceptions import RequestException

# --------------------------------------------------------------------------------------
# Constants declaration

SEPARATOR_CONSTANT = "\r\r\r\n\r\r\r"

API_VERSION =  "v3"

# Polling retry configuration (used when waiting for operations to finish)
POLL_MAX_RETRIES = 6                # consecutive failures tolerated before giving up
POLL_RETRY_DELAY_SECONDS = 5        # wait between retries
POLL_REQUEST_TIMEOUT_SECONDS = 60   # per-request network timeout

# Upload configuration (a file is sent to the server in chunks)
UPLOAD_CHUNK_SIZE_BYTES = 200000        # same chunk size the web and desktop clients use
UPLOAD_REQUEST_TIMEOUT_SECONDS = 120    # per-chunk network timeout
UPLOAD_MAX_RESUME_ATTEMPTS = 5          # bounded so a link that keeps dropping does not retry forever

# Script operation configuration
SCRIPT_ASSOCIATION_SELECTION_WHEN_RUNNING = -1   # sentinel stored in A={} when the association is chosen when the script is executed

# Integration groups (folders) configuration
UNGROUPED_GROUP_ID = -1   # group id the server uses for imports, exports and scripts that are not inside any group

# --------------------------------------------------------------------------------------
# CorporateServer class

class CorporateServer:
    def __init__(self, base_url, login_name, password, console_feedback=True):
        self.__instance_with_token = False
        self.__base_url = base_url
        self.__login_name = login_name
        self.__password = password
        self.__logged_username = ""
        self.__logged_user_id = -1
        self.__session_token = ""
        self.__selected_model_id = -1
        self.__default_idiom_id = 1
        self.__console_feedback = console_feedback

    @classmethod
    def instance_with_token(cls, base_url, token, console_feedback=True):
        corporate_server = cls(base_url, "", "", console_feedback)
        corporate_server.__session_token = token
        corporate_server.__instance_with_token = True
        return corporate_server

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

    def __call_with_retry(self, func, description,
                          max_retries=POLL_MAX_RETRIES,
                          retry_delay=POLL_RETRY_DELAY_SECONDS):
        """Call `func` and retry on any exception, up to `max_retries` consecutive
           attempts. Re-raises the last exception only after all attempts fail.

            Parameters:
            func (callable): The zero-argument callable to invoke
            description (string): Text used for progress feedback and the final error
            max_retries (int): Maximum number of consecutive attempts before giving up
            retry_delay (int): Seconds to wait between attempts

            Returns:
            Whatever `func` returns on success, or raises an Exception if every
            attempt fails.
        """
        last_ex = None
        for attempt in range(1, max_retries + 1):
            try:
                return func()
            except Exception as ex:
                last_ex = ex
                if attempt < max_retries:
                    if self.__console_feedback:
                        print(f"\r{description}...(retry {attempt}/{max_retries - 1})\033[K",
                              end="", flush=True)
                    time.sleep(retry_delay)
        raise Exception(f"{description} failed after {max_retries} attempts. "
                        f"Last error: {last_ex}") from last_ex

    def __get_models(self):
        # Set URL
        url = f"{self.__base_url}/{API_VERSION}/modeling/models"

        # Make GET request
        response = requests.get(url, headers=self.__get_default_headers(), timeout=POLL_REQUEST_TIMEOUT_SECONDS)

        # Check response
        if CorporateServer.__status_code_ok(response.status_code):
            data = response.json()
            return data
        else:
            raise Exception(f"Error getting models. Error details: {get_error_message_from_response(response.content)}")

    def __get_model_id(self,model_reference):
        # Get models
        models = self.__get_models()

        # Search for desired model (and return its ID if found)
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
        url = f"{self.__base_url}/{API_VERSION}/base/export-templates"

        # Make GET request
        response = requests.get(url, headers=self.__get_default_headers())

        # Check response
        if CorporateServer.__status_code_ok(response.status_code):
            data = response.json()
            return data
        else:
            raise Exception(f"Error getting export templates. Error details: {get_error_message_from_response(response.content)}")

    def __get_export_template_id(self,export_template_name):
        # Get export templates
        export_templates = self.__get_export_templates()

        # Search for desired model (and return its ID if found)
        for export_template in export_templates:
            if export_template['Name'].upper() == export_template_name.upper():
                return export_template['Id']

        # Model not found, generate exception
        raise Exception(f"Export template {export_template_name} not found")

    def __get_import_groups(self):
        # Set URL
        url = f"{self.__base_url}/{API_VERSION}/integration/import-groups"

        # Make GET request
        response = requests.get(url, headers=self.__get_default_headers())

        # Check response
        if CorporateServer.__status_code_ok(response.status_code):
            # We got a JSON with the import group list, just return it
            data = response.json()
            return data
        else:
            raise Exception(f"Error getting import groups. Error details: {get_error_message_from_response(response.content)}")

    def __get_import_group_id(self, group_reference):
        # No group reference means the import is not inside any group
        if group_reference is None:
            return UNGROUPED_GROUP_ID

        # Get import groups
        import_groups = self.__get_import_groups()

        # Search for desired import group (and return its ID if found)
        for import_group in import_groups:
            if import_group['Reference'] == group_reference:
                return import_group['Id']

        # Import group not found, generate exception
        raise Exception(f"Import group {group_reference} not found")

    def __get_imports(self, group_id):
        # Set URL & parameters (the server lists the imports of one group at a time)
        url = f"{self.__base_url}/{API_VERSION}/integration/imports"
        params = { "groupId": group_id }

        # Make GET request
        response = requests.get(url, params=params, headers=self.__get_default_headers())

        # Check response
        if CorporateServer.__status_code_ok(response.status_code):
            # We got a JSON with the groups and the imports of that level, only the imports are needed here
            data = response.json()
            return data['Imports']
        else:
            raise Exception(f"Error getting imports. Error details: {get_error_message_from_response(response.content)}")

    def __get_import_id(self, import_reference, group_reference=None):
        # Get imports of the informed group (or the ones outside any group)
        imports = self.__get_imports(self.__get_import_group_id(group_reference))

        # Search for desired import (and return its ID if found)
        for imp in imports:
            if imp['Reference'] == import_reference:
                return imp['Id']

        # Import not found, generate exception
        if group_reference is None:
            raise Exception(f"Import {import_reference} not found")
        else:
            raise Exception(f"Import {import_reference} not found in group {group_reference}")

    def __get_export_groups(self):
        # Set URL
        url = f"{self.__base_url}/{API_VERSION}/integration/export-groups"

        # Make GET request
        response = requests.get(url, headers=self.__get_default_headers())

        # Check response
        if CorporateServer.__status_code_ok(response.status_code):
            # We got a JSON with the export group list, just return it
            data = response.json()
            return data
        else:
            raise Exception(f"Error getting export groups. Error details: {get_error_message_from_response(response.content)}")

    def __get_export_group_id(self, group_reference):
        # No group reference means the export is not inside any group
        if group_reference is None:
            return UNGROUPED_GROUP_ID

        # Get export groups
        export_groups = self.__get_export_groups()

        # Search for desired export group (and return its ID if found)
        for export_group in export_groups:
            if export_group['Reference'] == group_reference:
                return export_group['Id']

        # Export group not found, generate exception
        raise Exception(f"Export group {group_reference} not found")

    def __get_exports(self, group_id):
        # Set URL & parameters (the server lists the exports of one group at a time)
        url = f"{self.__base_url}/{API_VERSION}/integration/exports"
        params = { "groupId": group_id }

        # Make GET request
        response = requests.get(url, params=params, headers=self.__get_default_headers())

        # Check response
        if CorporateServer.__status_code_ok(response.status_code):
            # We got a JSON with the groups and the exports of that level, only the exports are needed here
            data = response.json()
            return data['Exports']
        else:
            raise Exception(f"Error getting exports. Error details: {get_error_message_from_response(response.content)}")

    def __get_export(self, export_id):
        # Set URL
        url = f"{self.__base_url}/{API_VERSION}/integration/exports/{export_id}"

        # Make GET request
        response = requests.get(url, headers=self.__get_default_headers())

        # Check response (the server answers 204 with an empty body when the export does not exist)
        if response.status_code == 204:
            raise Exception(f"Export with id {export_id} not found")
        elif CorporateServer.__status_code_ok(response.status_code):
            # We got a JSON with the export, just return it
            data = response.json()
            return data
        else:
            raise Exception(f"Error getting export. Error details: {get_error_message_from_response(response.content)}")

    def __get_export_id(self, export_reference, group_reference=None):
        # Get exports of the informed group (or the ones outside any group)
        exports = self.__get_exports(self.__get_export_group_id(group_reference))

        # Search for desired export (and return its ID if found)
        for exp in exports:
            if exp['Reference'] == export_reference:
                return exp['Id']

        # Export not found, generate exception
        if group_reference is None:
            raise Exception(f"Export {export_reference} not found")
        else:
            raise Exception(f"Export {export_reference} not found in group {group_reference}")

    def __get_script_groups(self):
        # Set URL
        url = f"{self.__base_url}/{API_VERSION}/integration/script-groups"

        # Make GET request
        response = requests.get(url, headers=self.__get_default_headers())

        # Check response
        if CorporateServer.__status_code_ok(response.status_code):
            # We got a JSON with the script group list, just return it
            data = response.json()
            return data
        else:
            raise Exception(f"Error getting script groups. Error details: {get_error_message_from_response(response.content)}")

    def __get_script_group_id(self, group_reference):
        # No group reference means the script is not inside any group
        if group_reference is None:
            return UNGROUPED_GROUP_ID

        # Get script groups
        script_groups = self.__get_script_groups()

        # Search for desired script group (and return its ID if found)
        for script_group in script_groups:
            if script_group['Reference'] == group_reference:
                return script_group['Id']

        # Script group not found, generate exception
        raise Exception(f"Script group {group_reference} not found")

    def __get_scripts(self, group_id):
        # Set URL & parameters (the server lists the scripts of one group at a time)
        url = f"{self.__base_url}/{API_VERSION}/integration/scripts"
        params = { "groupId": group_id }

        # Make GET request
        response = requests.get(url, params=params, headers=self.__get_default_headers())

        # Check response
        if CorporateServer.__status_code_ok(response.status_code):
            # We got a JSON with the groups and the scripts of that level, only the scripts are needed here
            data = response.json()
            return data['Scripts']
        else:
            raise Exception(f"Error getting scripts. Error details: {get_error_message_from_response(response.content)}")

    def __get_script_id(self, reference, group_reference=None):
        # Get scripts of the informed group (or the ones outside any group)
        scripts = self.__get_scripts(self.__get_script_group_id(group_reference))

        # Search for desired script (and return its ID if found)
        for scr in scripts:
            if scr['Reference'] == reference:
                return scr['Id']

        # Script not found, generate exception
        if group_reference is None:
            raise Exception(f"Script {reference} not found")
        else:
            raise Exception(f"Script {reference} not found in group {group_reference}")

    def __get_script_operations(self, script_id):
        # Set URL
        url = f"{self.__base_url}/{API_VERSION}/integration/scripts/{script_id}/operations"

        # Make GET request
        response = requests.get(url, headers=self.__get_default_headers())

        # Check response
        if CorporateServer.__status_code_ok(response.status_code):
            # We got a JSON with the script operations list, just return it
            data = response.json()
            return data
        else:
            raise Exception(f"Error getting script operations. Error details: {get_error_message_from_response(response.content)}")

    def __get_script_runtime_associations(self, script_id):
        # Set URL
        url = f"{self.__base_url}/{API_VERSION}/integration/scripts/{script_id}/runtime-associations"

        # Make GET request
        response = requests.get(url, headers=self.__get_default_headers())

        # Check response (servers older than the runtime association feature do not have this route)
        if response.status_code == 404:
            return { "Required": False, "Associations": [] }
        elif CorporateServer.__status_code_ok(response.status_code):
            # We got a JSON telling if an association is required and which ones may be used
            data = response.json()
            return data
        else:
            raise Exception(f"Error getting script runtime associations. Error details: {get_error_message_from_response(response.content)}")

    def __get_cubes(self):
        # Set URL
        url = f"{self.__base_url}/{API_VERSION}/analysis/cubes"

        # Make GET request
        response = requests.get(url, headers=self.__get_default_headers())

        # Check response
        if CorporateServer.__status_code_ok(response.status_code):
            # We got a JSON with the cube list, just return it
            data = json.loads(response.text)
            return data
        else:
            raise Exception(f"Error getting cubes. Error details: {get_error_message_from_response(response.content)}")

    def __get_cube_id(self, reference):
        # Get cubes
        cubes = self.__get_cubes()

        # Search for desired cube (and return its ID if found)
        for cube in cubes:
            if cube['Reference'] == reference:
                return cube['Id']

        # Cube not found, generate exception
        raise Exception(f"Cube {reference} not found")

    def __get_facts(self):
        # Set URL
        url = f"{self.__base_url}/{API_VERSION}/analysis/facts"

        # Make GET request
        response = requests.get(url, headers=self.__get_default_headers())

        # Check response
        if CorporateServer.__status_code_ok(response.status_code):
            # We got a JSON with the import list, just return it
            data = response.json()
            return data
        else:
            raise Exception(f"Error getting facts. Error details: {get_error_message_from_response(response.content)}")

    def __get_fact_id(self, fact_reference, processable_only=False):
        # Get facts
        facts = self.__get_facts()

        # Search for desired fact (and return its ID if found)
        for fact in facts:
            if fact['Reference'] == fact_reference:
                if fact['FactType'] != AbmFactType.CrossModule and processable_only:
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
        url = f"{self.__base_url}/{API_VERSION}/base/files"
        params = { "fileType": -1 }

        # Make GET request
        response = requests.get(url, headers=self.__get_default_headers(), params=params)

        # Check response
        if CorporateServer.__status_code_ok(response.status_code):
            data = response.json()
            return data
        else:
            raise Exception(f"Error getting files. Error details: {get_error_message_from_response(response.content)}")

    def __get_file_id(self,file_name, username=""):
        # Get files
        files = self.__get_files()

        # Define who we should pick as file's owner (username parameter if passed or current logged user)
        target_user = (username if username != "" else self.__logged_username)

        # Search for desired file (and return its ID if found)
        for file in files:
            if file['FileName'].upper() == file_name.upper() and file['UserName'].upper() == target_user.upper():
                return file['Id']

        # File not found, generate exception
        raise Exception(f"File {file_name} not found for user {target_user}")

    def __get_etl_executables(self):
        # Set URL
        url = f"{self.__base_url}/{API_VERSION}/base/etl-executables"

        # Make GET request
        response = requests.get(url, headers=self.__get_default_headers())

        # Check response
        if CorporateServer.__status_code_ok(response.status_code):
            data = response.json()
            return data
        else:
            raise Exception(f"Error getting ETL executables. Error details: {get_error_message_from_response(response.content)}")

    def __store_logged_user_details(self):
        # Set URL
        url = f"{self.__base_url}/{API_VERSION}/base/users/logged/profile"

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
            raise Exception(f"Error getting and storing user details. Error details: {get_error_message_from_response(response.content)}")

    def __store_selected_model(self):
        # Set URL
        url = f"{self.__base_url}/{API_VERSION}/modeling/models/selected"

        # Make GET request
        response = requests.get(url, headers=self.__get_default_headers())

        # Check response (the server answers 204 with an empty body when the session has no model selected)
        if response.status_code == 204:
            self.__selected_model_id = -1
        elif CorporateServer.__status_code_ok(response.status_code):
            # Store the id of the model already selected in this session
            data = response.json()
            self.__selected_model_id = data.get("Id")
        else:
            raise Exception(f"Error getting selected model. Error details: {get_error_message_from_response(response.content)}")

    def __get_available_associations(self):
        # Set URL & parameters
        url = f"{self.__base_url}/{API_VERSION}/modeling/models/available-associations"
        params = { "modelId" : self.__selected_model_id }

        # Make GET request
        response = requests.get(url, params=params, headers=self.__get_default_headers())

        # Check response
        if CorporateServer.__status_code_ok(response.status_code):
            # Return JSON with list of available associations
            data = response.json()
            return data
        else:
            # Something got wrong, generate exception with status code
            raise Exception(f"Error model associations. Error details: {get_error_message_from_response(response.content)}")

    def __get_association_id(self, period_reference, scenario_reference):
        # Get available associations
        associations = self.__get_available_associations()

        # Search for desired association (and return its ID if found)
        for association in associations:
            if association['PeriodReference'] == period_reference and association['ScenarioReference'] == scenario_reference:
                return association['Id']

        # Association not found, generate exception
        raise Exception(f"Association {period_reference}/{scenario_reference} not found")

    def __get_default_association_id(self, period_scenario):
        # The period/scenario may be informed by reference (documented) or by name (older scripts)
        for association in self.__get_available_associations():
            by_reference = f"{association.get('PeriodReference')}/{association.get('ScenarioReference')}"
            by_name = f"{association.get('PeriodName')}/{association.get('ScenarioName')}"
            if period_scenario.upper() in (by_reference.upper(), by_name.upper()):
                return association.get("Id")

        # Association not found, generate exception
        raise Exception(f"Period/scenario {period_scenario} not found")

    def __get_operation_status(self, operation_id):
        # Set URL & parameters
        url = f"{self.__base_url}/{API_VERSION}/base/operations/{operation_id}/status"
        params = { "cultureInfo" : "en-US" }

        # Make GET request
        response = requests.get(url, params=params, headers=self.__get_default_headers(), timeout=POLL_REQUEST_TIMEOUT_SECONDS)

        # Check response
        if CorporateServer.__status_code_ok(response.status_code):
            # Return JSON with the operation status
            return response.json()
        else:
            # Something got wrong, generate exception
            raise Exception(f"Error waiting for operation to finish. Error details: {get_error_message_from_response(response.content)}")

    def __wait_for_operation_to_finish(self, operation_id):
        # Setup helper variables to display our "visual progress indicator"
        signs = ["-", "\\", "|", "/",  "-",  "\\",  "|",  "/"]
        sign_pos = 0

        # Shot our initial "progress indicator"
        if self.__console_feedback:
            print("[-]", end="", flush=True)

        # Keep checking every 1 second until operation finishes
        condition = False
        while not condition:
            # Get operation status (retried on transient failures)
            data = self.__call_with_retry(
                lambda: self.__get_operation_status(operation_id),
                "Waiting for operation to finish")

            # Check status and return if aborted/finished or wait 1 second and try again
            if data.get("OperationStatus") == AbmOperationStatus.Aborted or data.get("OperationStatus") == AbmOperationStatus.Finished:
                condition = True
            else:
                time.sleep(2)
                if self.__console_feedback:
                    print(f"\b\b\b[{signs[sign_pos]}]", end="", flush=True)
                    sign_pos = sign_pos + 1 if sign_pos < 7 else 0

        # Overwrite our "progress indicator" with spaces
        if self.__console_feedback:
            print(f"\b\b\b   \b\b\b", end="", flush=True)

    def __get_script_operations_in_group(self, group_id):
        # Set URL & parameters
        url = f"{self.__base_url}/{API_VERSION}/base/operations/in-group"
        params = { "groupId" : group_id, "pending" : False, "cultureInfo": self.__default_idiom_id }

        # Make GET request
        response = requests.get(url, params=params, headers=self.__get_default_headers(), timeout=POLL_REQUEST_TIMEOUT_SECONDS)

        # Check response
        if CorporateServer.__status_code_ok(response.status_code):
            # Return JSON with list of scheduled operations
            return response.json()
        else:
            # Something got wrong, generate exception with status code
            raise Exception(f"Error getting pending operations in group {group_id}. Error details: {get_error_message_from_response(response.content)}")

    def __get_session_token(self):
        """Get current session token

            Returns:
            string: session token or empty string
        """
        return self.__session_token

    def __get_idiom_id(self, idiom_code):
        """Get idiom id by code

            Parameters:
            idiom_code (string): Idiom code (ex: en-US, pt-BR)

            Returns:
            int: Idiom id or -1 if not found
        """
        # Set URL
        url = f"{self.__base_url}/{API_VERSION}/base/idioms"

        # Make GET request
        response = requests.get(url, headers=self.__get_default_headers())

        # Parse response (casting the response to a List[Dict] so we can use it later
        data: List[Dict] = response.json()

        # Search for desired idiom (and return its ID if found)
        found_id = next(
            (item['Id'] for item in data if item.get('Code').upper() == idiom_code.upper()),
            -1
        )

        return found_id

    def __etl_operation_matches(self, operation_details, etl_token):
        """Check if a script ETL operation runs the ETL package named in an execute_script parameter

            Parameters:
            operation_details (string): Details stored in the script operation. The server stores the fields separated
                                        by SEPARATOR_CONSTANT in this order: type, file id, server, database,
                                        integrated security, user, password and shared file name
            etl_token (string): ETL part of the parameter, starting with an executable id ("1;FILE.etlx",
                                "1;FILE.etlx;SHARED" or "2;server;database;integrated_security;user;password")

            Returns:
            True if the operation runs that ETL package, otherwise False
        """
        etl_params = [param.strip() for param in etl_token.split(";")]

        # The executable tells whether the remaining fields describe a file or a database
        if not etl_params[0].isdigit():
            raise Exception(f"ExecutableId parameter '{etl_token}' is invalid.")

        executable_id = int(etl_params[0])
        executable_type = self.get_etl_executable_type(executable_id)

        # Every ETL operation stores at least the first 7 fields
        fields = [field.strip() for field in operation_details.split(SEPARATOR_CONSTANT)]
        if len(fields) < 7:
            return False

        if executable_type == AbmEtlType.File:
            # ETL file: a file store file is identified by its id, a shared file by its name (eighth field)
            if len(etl_params) < 2 or etl_params[1] == "":
                raise Exception(f"FileName parameter '{etl_token}' is invalid.")

            file_name = etl_params[1]
            is_shared_file = (len(etl_params) == 3 and etl_params[2].upper() == "SHARED")

            if fields[0] != str(executable_id):
                return False
            if is_shared_file:
                return len(fields) >= 8 and fields[7].upper() == file_name.upper()
            else:
                return fields[1] == str(self.__get_file_id(file_name))

        if executable_type == AbmEtlType.Database:
            # ETL database: identified by server, database and user
            if len(etl_params) != 6:
                raise Exception(f"Invalid parameters '{etl_token}' to EtlPackage operation.")

            server_name = etl_params[1]
            database_name = etl_params[2]
            user_name = etl_params[4]

            return fields[0] == str(executable_id) and fields[2].upper() == server_name.upper() and fields[3].upper() == database_name.upper() and fields[5].upper() == user_name.upper()

        # Unsupported ETL type
        return False

    def __get_uploaded_bytes(self, file_guid):
        """How many bytes of a chunked upload the server already holds

            Returns -1 when the answer cannot be trusted, which is also what a server without the
            endpoint produces, so in that case the caller simply gives up on resuming.
        """
        try:
            url = f"{self.__base_url}/{API_VERSION}/base/files/upload-status"

            response = requests.get(url, params={'fileGuid': file_guid},
                                    headers=self.__get_default_headers(),
                                    timeout=POLL_REQUEST_TIMEOUT_SECONDS)

            if not CorporateServer.__status_code_ok(response.status_code):
                return -1

            data = response.json()

            # Nothing on the server means the upload starts over from the first byte
            if not data.get('Exists', False):
                return 0

            return data.get('BytesReceived', -1)
        except Exception:
            # Not being able to ask is not an upload failure, it only means this upload cannot be
            # resumed. Older servers answer 404 here.
            return -1

    @staticmethod
    def __is_resumable_upload_failure(ex):
        """Tells a transport failure, where resuming makes sense, from a server that answered with
           an error status

            When the server rejected the chunk it already decided about those bytes, so sending them
            again changes nothing and only wastes the whole transfer. Written as an allowlist on
            purpose: an exception nobody predicted must not silently become a retry of the entire file.
        """
        # RequestException covers connection errors and timeouts raised by requests, OSError covers
        # a raw socket or file error underneath it
        return isinstance(ex, (RequestException, OSError))

    def __abort_upload(self, file_guid):
        """Drops the partial temporary file of an upload that will not be finished"""
        try:
            url = f"{self.__base_url}/{API_VERSION}/base/files/upload/{file_guid}"

            requests.delete(url, headers=self.__get_default_headers(),
                            timeout=POLL_REQUEST_TIMEOUT_SECONDS)
        except Exception:
            # Best effort, the server drops the partial file on its own later
            pass

    def __send_upload_chunks(self, file, url, headers, base_name, file_guid, file_size, file_type,
                             replace_existing, chunk_size, progress_callback, bytes_already_sent):
        """Sends the file from its current position to the end, one request per chunk

            Chunks are numbered from the current position, because the server only compares Index
            against TotalCount - 1 to recognize the last chunk of an upload and ignores where that
            chunk sits in the file. That is what makes resuming possible.

            Returns True when every chunk was sent, or False when progress_callback stopped it.
            Raises if a chunk fails, so the caller can decide whether to resume.
        """
        bytes_sent = bytes_already_sent
        remaining = file_size - bytes_sent

        # Ceiling division. An empty file still needs one request, otherwise the server never
        # assembles it
        chunk_count = max(1, -(-remaining // chunk_size))

        for chunk_index in range(chunk_count):
            # Asked before spending the request, so stopping never leaves a half written chunk
            # behind. Without its last chunk the server never assembles the file.
            if progress_callback is not None:
                if progress_callback(base_name, bytes_sent, file_size, chunk_index, chunk_count) is False:
                    return False

            chunk = file.read(chunk_size)

            # Set chunk & data
            files =  {
                'file': (base_name, chunk, 'application/octet-stream')
            }
            data = {
                'chunkMetadata': f"{{\"FileName\": \"{base_name}\", \"Index\": {chunk_index}, \"TotalCount\": {chunk_count}, \"FileSize\": {str(file_size)}, \"FileType\": \"\", \"FileGuid\": \"{file_guid}\"}}",
                "FileType": file_type,
                "ReplaceExistingFile": replace_existing,
                "FileStoreUserId": self.__logged_user_id
            }

            # Make POST request.
            # A failed chunk is never resent as is, and this is deliberately NOT wrapped in
            # __call_with_retry: the server appends whatever arrives, so resending a chunk that
            # already landed would duplicate its bytes in the assembled file. The caller asks the
            # server where it stopped before continuing.
            response = requests.post(url, headers=headers, files=files, data=data,
                                     timeout=UPLOAD_REQUEST_TIMEOUT_SECONDS)

            # Check response
            if not CorporateServer.__status_code_ok(response.status_code):
                raise Exception(f"Error uploading chunk {chunk_index + 1} of {chunk_count} "
                                f"(Status code: {response.status_code}. Text: {response.text})")

            bytes_sent += len(chunk)

        return True

    def logon(self):
        """Logon to MyABCM Corporate using the credentials informed when creating the CorporateServer object

            Returns:
            Nothing if logon is successful or an Exception if it fails for any reason
        """
        if self.__instance_with_token:
            if self.__console_feedback: print(f"Logging on with token {self.__session_token}...", end="")
            self.__store_logged_user_details()
            # The session behind the token may already have a model selected, so pick it up here
            self.__store_selected_model()
        else:
            if self.__console_feedback: print(f"Logging on to {self.__base_url} using user {self.__login_name}...", end="")

            # Set URL & parameters
            url = f"{self.__base_url}/{API_VERSION}/base/logon"
            body = {"Username": self.__login_name, "Password": self.__password, "ClientIPAddress": "127.0.0.1" }

            # Make POST request
            response = requests.post(url, json=body)

            # Check response
            if CorporateServer.__status_code_ok(response.status_code):
                data = response.json()

                if data.get("Result") == LogonResult.Ok:
                    # Login successful, store session token
                    self.__session_token = data.get("SessionToken")
                    # Store additional user details
                    self.__store_logged_user_details()

                    if self.__console_feedback: print("ok")
                else:
                    if self.__console_feedback: print(f"failed")

                    # Login failed, generate custom exception based on result code
                    if data.get("Result") == LogonResult.PasswordExpired:
                        raise Exception("Error logging in (Password expired)")
                    if data.get("Result") == LogonResult.ProductNotAuthorized:
                        raise Exception("Error logging in (Product not authorized)")
                    if data.get("Result") == LogonResult.NoLicenseAvailable:
                        raise Exception("Error logging in (License not available)")
                    if data.get("Result") == LogonResult.UserNotAuthorized:
                        raise Exception("Error logging in (User not authorized expired)")

                    # Result code not in 6 to 9 range, generate generic exception with result code
                    raise Exception(f"Error logging in (Logon result code: {LogonResult(data.get('Result')).name})")
            else:
                # Something got wrong, generate exception with status code
                raise Exception(f"Error logging in. Error details: {get_error_message_from_response(response.content)}")

    def logoff(self):
        """Logoff from MyABCM Corporate

            Returns:
            Nothing if logoff is successful or an Exception if it fails for any reason
        """
        if self.__instance_with_token:
            if self.__console_feedback: print(f"Logging off with token {self.__session_token} ...", end="")
        else:
            if self.__console_feedback: print(f"Logging off from {self.__base_url} using user {self.__login_name}...", end="")

        # Set URL & parameters
        url = f"{self.__base_url}/{API_VERSION}/base/logoff"
        body = {"ClientIPAddress": "127.0.0.1"}

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check response
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")

            raise Exception(f"Error logging off. Error details: {get_error_message_from_response(response.content)}")
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
        url = f"{self.__base_url}/{API_VERSION}/modeling/models/selected"
        body = {"ModelId": model_id}

        # Make GET request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check response
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("Failed")

            raise Exception(f"Error selecting model. Error details: {get_error_message_from_response(response.content)}")
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
            description (string): Description of the model
            audit_level (int): Audit level. Possible values are: 0 (for Disabled), 1 (for Basic), 2 (for Intermediate) or 3 (for Complete)

            Returns:
            Nothing if model is created or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Adding new model {name} ({reference})...", end="")

        # Set URL & parameters
        url = f"{self.__base_url}/{API_VERSION}/modeling/models"
        body = { "Name": name, "Reference": reference, "Description": description, "AuditLevel": audit_level, "OwnerId": self.__logged_user_id }

        # Make GET request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check response
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")

            raise Exception(f"Error creating model (Status code: {get_error_message_from_response(response.content)})")
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
        url = f"{self.__base_url}/{API_VERSION}/modeling/models"
        params = { "ids" : model_id }

        # Make DELETE request
        response = requests.delete(url, params=params, headers=self.__get_default_headers())

        # Check response
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")

            raise Exception(f"Error removing model. Error details: {get_error_message_from_response(response.content)}")

        # Loop and wait for model to be deleted (existence check retried on transient failures)
        condition = True
        while condition:
            condition = self.__call_with_retry(
                lambda: self.__model_exists(reference),
                f"Removing model {reference} from server")

            if self.__console_feedback: print(".", end= "")
            time.sleep(2)
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
        url = f"{self.__base_url}/{API_VERSION}/modeling/models/selected/calculate"
        body = {"PeriodScenarioIds": [association_id],
                "OperationDate":  CorporateServer.__get_current_utc_iso8601(),
                "NotifyByEmail": notify_by_email
                }

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check response
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error starting model calculation. Error details: {get_error_message_from_response(response.content)}")

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

        # Search for desired file (and return its ID if found)
        for file in files:
            if file['FileName'].upper() == file_name.upper() and file['UserName'].upper() == target_user.upper():
                return True

        return False

    def upload_file(self, file_name, file_type, replace_existing,
                    progress_callback=None, chunk_size=UPLOAD_CHUNK_SIZE_BYTES):
        """Upload file to the server

            The file is sent in chunks, so a large file over a poor connection does not depend on
            one long request, and so the upload can be stopped between chunks. When a chunk fails,
            the server is asked how much it already holds and the upload continues from there.

            Parameters:
            file_name (string): Complete name of the local file to be uploaded
            file_type (integer): Type of the file (0 = Excel, 1 = Access, 2 = ETL/X, 3 = CSV)
            replace_existing (integer): 1 for replacing existing file or 0 to not replace it
            progress_callback (callable): Optional, called before each chunk is sent as
                                          progress_callback(file_name, bytes_sent, total_bytes,
                                          chunk_index, chunk_count). Return False to stop the
                                          upload, any other value continues it
            chunk_size (integer): Size in bytes of each chunk sent to the server

            Returns:
            True if the file is uploaded, False if progress_callback stopped the upload,
            or an Exception if it fails for any reason
        """
        if chunk_size <= 0:
            raise ValueError(f"chunk_size must be greater than zero (got {chunk_size})")

        if self.__console_feedback: print(f"Uploading file {file_name}...", end="")

        # Set URL
        url = f"{self.__base_url}/{API_VERSION}/base/files"

        # Set header with authorization
        # We don't use the default header used in all ather calls as we do not
        # want the default content type "application/json" in this call
        headers = {
            'Authorization': f'Bearer {self.__session_token}'
        }

        base_name = os.path.basename(file_name)
        file_size = os.path.getsize(file_name)

        # The server names the temporary file it appends every chunk to after this value, so the
        # whole file has to travel under a single guid. It stays the same across resume attempts,
        # as that is what identifies the upload on the server.
        file_guid = str(uuid.uuid4())

        # Open local file for reading and call the REST API once per chunk
        with open(file_name, 'rb') as file:
            bytes_sent = 0
            resume_attempts = 0

            while True:
                try:
                    if not self.__send_upload_chunks(file, url, headers, base_name, file_guid,
                                                    file_size, file_type, replace_existing,
                                                    chunk_size, progress_callback, bytes_sent):
                        # Stopped on purpose, so free the partial file on the server right away
                        self.__abort_upload(file_guid)
                        if self.__console_feedback: print("cancelled")
                        return False

                    break

                except Exception as ex:
                    # The server answering with an error status is a decision about these bytes, not
                    # a transport hiccup, so it is reported instead of resumed
                    if not CorporateServer.__is_resumable_upload_failure(ex):
                        if self.__console_feedback: print("failed")
                        raise

                    resume_attempts += 1

                    if resume_attempts <= UPLOAD_MAX_RESUME_ATTEMPTS:
                        uploaded_bytes = self.__get_uploaded_bytes(file_guid)
                    else:
                        uploaded_bytes = -1

                    # Resuming needs a server that answered how much it holds and bytes still
                    # missing to make progress with. Anything else and the failure is reported as
                    # it always was.
                    if uploaded_bytes < 0 or uploaded_bytes >= file_size:
                        if self.__console_feedback: print("failed")
                        raise

                    bytes_sent = uploaded_bytes
                    file.seek(bytes_sent)

        # Final report, so a caller following the upload can show it as complete
        if progress_callback is not None:
            progress_callback(base_name, file_size, file_size, 1, 1)

        if self.__console_feedback: print("ok")
        return True

    def download_file(self, file_name, local_path):
        """Download file from the server

        Parameters:
        file_name (string): Name of the file to be downloaded
        local_path (string): Path where to save the file

        Returns:
        File requested or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Downloading file {file_name}...", end="")

        # Get the ID of the file to be downloaded (assuming here the current logged user is the file owner)
        file_id = self.__get_file_id(file_name)

        # Set URL
        url = f"{self.__base_url}/{API_VERSION}/base/files/{file_id}/download"

        # Make GET request
        response = requests.get(url, headers=self.__get_default_headers())

        # Check response
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Failed to download {file_name}. Status code: {response.status_code}")
        else:
            with open(f"{local_path}\\{file_name}", "wb") as file:
                file.write(response.content)
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

        # Get the ID of the file to be removed (assuming here the current logged user is the file owner)
        file_id = self.__get_file_id(file_name)

        # Set URL & parameters
        url = f"{self.__base_url}/{API_VERSION}/base/files"
        params = { "ids": file_id }

        # Make DELETE request
        response = requests.delete(url, headers=self.__get_default_headers(), params=params)

        # Check response
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error removing file {file_name} (Status code: {response.status_code}. Text: {response.text})")
        else:
            if self.__console_feedback: print("ok")

    def import_group_exists(self, reference):
        """Check if import group (folder) exists

            Parameters:
            reference (string): Reference of the import group

            Returns:
            True if it exists, otherwise False
        """
        if self.__console_feedback: print(f"Checking if import group exists {reference}...", end="")
        # Get import groups
        import_groups = self.__get_import_groups()

        # Search for desired import group (and return True if found)
        for import_group in import_groups:
            if import_group['Reference'] == reference:
                if self.__console_feedback: print("yes")
                return True

        if self.__console_feedback: print("no")
        return False

    def add_import_group(self, name, reference, description):
        """Add a new import group (folder) to the selected model

            Parameters:
            name (string): Name of the import group
            reference (string): Reference of the import group
            description (string): Description of the import group

            Returns:
            Nothing if import group is created or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Adding new import group {name} ({reference})...", end="")

        # Set URL & parameters
        url = f"{self.__base_url}/{API_VERSION}/integration/import-groups"
        body = { "Name": name, "Reference": reference, "Description": description }

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check response
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error creating import group. Error details: {get_error_message_from_response(response.content)}")
        else:
            if self.__console_feedback: print("ok")

    def remove_import_group(self, reference):
        """Remove an existing import group (folder)

            Parameters:
            reference (string): Reference of the import group

            Returns:
            Nothing if import group is removed or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Removing import group {reference}...", end="")

        # Get import group id
        import_group_id = self.__get_import_group_id(reference)

        # Set URL
        url = f"{self.__base_url}/{API_VERSION}/integration/import-groups/{import_group_id}"

        # Make DELETE request
        response = requests.delete(url, headers=self.__get_default_headers())

        # Check response
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error removing import group. Error details: {get_error_message_from_response(response.content)}")
        else:
            if self.__console_feedback: print("ok")

    def import_exists(self, reference, group_reference=None):
        """Check if import exists

            Parameters:
            reference (string): Reference of the import
            group_reference (string, optional): Reference of the group (folder) that contains the import. Omit for imports outside any group

            Returns:
            True if it exists, otherwise False
        """
        if self.__console_feedback: print(f"Checking if import exists {reference}...", end="")
        # Get imports of the informed group (or the ones outside any group)
        imports = self.__get_imports(self.__get_import_group_id(group_reference))

        # Search for desired import (and return True if found)
        for imp in imports:
            if imp['Reference'] == reference:
                if self.__console_feedback: print("yes")
                return True

        if self.__console_feedback: print("no")
        return False

    def add_import(self, parameters):
        """Add a new import to the selected model

            Parameters:
            parameters: Dictionary with all properties required for the import. For more info, check swagger documentation.
                        The optional property "ImportGroupReference" places the import inside an existing group (folder)

            Returns:
            Nothing if operation is successful or an Exception if it fails for any reason
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

        # Get the import group id (if ImportGroupReference is informed, otherwise the import is created outside any group)
        import_group_id = self.__get_import_group_id(parameters.get("ImportGroupReference"))

        # Store DataSourceType and DataSourceParameter in our helper variables
        datasource_type = parameters.get("DataSourceType")
        datasource_parameter = parameters.get("DataSourceParameter")

        # Validate datasource_type
        if not AbmDataSourceType.has_value(datasource_type):
            raise Exception("Invalid DataSourceType. Must be between 0 and 8")

        # Validate datasource_parameter (based on datasource_type)
        if datasource_type == AbmDataSourceType.Excel or datasource_type == AbmDataSourceType.Access or datasource_type == AbmDataSourceType.ETL:
            # Parameter is and EXCEL, ACCESS or ETL file, so get file it
            if self.file_exists(datasource_parameter):
                datasource_parameter = self.__get_file_id(datasource_parameter)
            else:
                raise Exception(f"File {datasource_parameter} not found in server for the current logged user")

        elif datasource_type == AbmDataSourceType.Internal:
            # Parameter is reference of the source model, so get it
            if self.model_exists(datasource_parameter):
                datasource_parameter = self.__get_model_id(datasource_parameter)
            else:
                raise Exception(f"Model {datasource_parameter} not found in server for the current logged user")

        elif datasource_type == AbmDataSourceType.DataMap:
            # Parameter is a DataMap, datasource parameter is ignored in this
            # case, so we set it to an empty string
            datasource_parameter =  ""

        elif datasource_type == AbmDataSourceType.SharedFile:
            pass

        # If datasource type is 2 (OLE DB), 3 (SQL Server), 4 (Oracle) or 8 (SharedFile) we just use the
        # datasource_parameter with no further validation

        # Set URL & parameters(body)
        url = f"{self.__base_url}/{API_VERSION}/integration/imports"
        body = {
            "Name": parameters.get("Name"),
            "Reference": parameters.get("Reference"),
            "Description": parameters.get("Description") if parameters.get("Description") is not None else "",
            "ImportGroupId": import_group_id,
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
            "PBGroups": parameters.get("PBGroups") if parameters.get("PBGroups") is not None else "",
            "PBPackages": parameters.get("PBPackages") if parameters.get("PBPackages") is not None else "",
            "PBItems": parameters.get("PBItems") if parameters.get("PBItems") is not None else "",
            "PBItemDimensions": parameters.get("PBItemDimensions") if parameters.get("PBItemDimensions") is not None else "",
            "PBItemAssociations": parameters.get("PBItemAssociations") if parameters.get("PBItemAssociations") is not None else "",
            "PBItemDetails": parameters.get("PBItemDetails") if parameters.get("PBItemDetails") is not None else "",
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
            raise Exception(f"Error adding import {parameters.get('Name')}. Error: {get_error_message_from_response(response.content)}")
        else:
            if self.__console_feedback: print("ok")

    def execute_import(self, reference, notify_by_email, idiom_code, use_transaction, group_reference=None):
        """Execute import (this function is synchronous and will wait for the imported to finish executing)

        Parameters:
        reference (string): Reference of the import
        notify_by_email (boolean): True for the user to be notified by email when the import ends or False for the user not to be notified
        idiom_code (string): Code of the idiom to be used
        use_transaction (boolean): True for using a transaction or False for not using a transaction
        group_reference (string, optional): Reference of the group (folder) that contains the import. Omit for imports outside any group

        Returns:
        Nothing if import is executed or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Execute import {reference}...", end="")

        # Get import id
        import_id = self.__get_import_id(reference, group_reference)

        #Get Idiom id
        idiom_id = self.__get_idiom_id(idiom_code)

        # Set URL & parameters
        url = f"{self.__base_url}/{API_VERSION}/integration/imports/{import_id}/execute"
        body = {"OperationDate":  CorporateServer.__get_current_utc_iso8601(),
                "NotifyByEmail": notify_by_email,
                "IdiomId": idiom_id if idiom_id != -1 else self.__default_idiom_id,
                "UseTransaction": use_transaction}

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error calling execute import. Error details: {get_error_message_from_response(response.content)}")

        # Read operation id (that is returned in response.text)
        operation_id =  response.text

        # Wait for operation to finish
        self.__wait_for_operation_to_finish(operation_id)

        if self.__console_feedback: print("ok");

    def remove_import(self, reference, group_reference=None):
        """Remove an existing import

            Parameters:
            reference (string): Reference of the import
            group_reference (string, optional): Reference of the group (folder) that contains the import. Omit for imports outside any group

            Returns:
            Nothing if import is removed or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Remove import {reference}...", end="")

        # Get import id
        import_id = self.__get_import_id(reference, group_reference)

        # Set URL
        url = f"{self.__base_url}/{API_VERSION}/integration/imports/{import_id}"

        # Make DELETE request
        response = requests.delete(url, headers=self.__get_default_headers())

        # Check response
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed");
            raise Exception(f"Error removing import. Error details: {get_error_message_from_response(response.content)}")
        else:
            if self.__console_feedback: print("ok");

    def export_group_exists(self, reference):
        """Check if export group (folder) exists

            Parameters:
            reference (string): Reference of the export group

            Returns:
            True if it exists, otherwise False
        """
        if self.__console_feedback: print(f"Checking if export group exists {reference}...", end="")
        # Get export groups
        export_groups = self.__get_export_groups()

        # Search for desired export group (and return True if found)
        for export_group in export_groups:
            if export_group['Reference'] == reference:
                if self.__console_feedback: print("yes")
                return True

        if self.__console_feedback: print("no")
        return False

    def add_export_group(self, name, reference, description):
        """Add a new export group (folder) to the selected model

            Parameters:
            name (string): Name of the export group
            reference (string): Reference of the export group
            description (string): Description of the export group

            Returns:
            Nothing if export group is created or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Adding new export group {name} ({reference})...", end="")

        # Set URL & parameters
        url = f"{self.__base_url}/{API_VERSION}/integration/export-groups"
        body = { "Name": name, "Reference": reference, "Description": description }

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check response
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error creating export group. Error details: {get_error_message_from_response(response.content)}")
        else:
            if self.__console_feedback: print("ok")

    def remove_export_group(self, reference):
        """Remove an existing export group (folder)

            Parameters:
            reference (string): Reference of the export group

            Returns:
            Nothing if export group is removed or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Removing export group {reference}...", end="")

        # Get export group id
        export_group_id = self.__get_export_group_id(reference)

        # Set URL
        url = f"{self.__base_url}/{API_VERSION}/integration/export-groups/{export_group_id}"

        # Make DELETE request
        response = requests.delete(url, headers=self.__get_default_headers())

        # Check response
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error removing export group. Error details: {get_error_message_from_response(response.content)}")
        else:
            if self.__console_feedback: print("ok")

    def add_export(self, parameters):
        """Add a new export to the selected model

            Parameters:
            parameters: Dictionary with all properties required for the export. For more info, check swagger documentation.
                        The optional property "ExportGroupReference" places the export inside an existing group (folder)

            Returns:
            Nothing if operation is successful or an Exception if it fails for any reason
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
        export_template_id = self.__get_export_template_id(parameters.get("ExportTemplateName")) if parameters.get(
            "ExportTemplateName") is not None else -1

        # Get the export group id (if ExportGroupReference is informed, otherwise the export is created outside any group)
        export_group_id = self.__get_export_group_id(parameters.get("ExportGroupReference"))

        # Store DataSourceType and DataSourceParameter in our helper variables
        datasource_type = parameters.get("DataSourceType")
        datasource_parameter = parameters.get("DataSourceParameter")

        # Validate datasource_type
        if not AbmDataSourceType.has_value(datasource_type) or datasource_type == AbmDataSourceType.Internal or datasource_type == AbmDataSourceType.DataMap:
            raise Exception("Invalid DataSourceType. Must be either 0, 1, 2, 3, 4, 5 or 8")

        # Validate datasource_parameter (based on datasource_type)
        if datasource_type == AbmDataSourceType.Excel or datasource_type == AbmDataSourceType.Access or datasource_type == AbmDataSourceType.ETL:
            # Parameter is and EXCEL, ACCESS or ETL file, so get file it
            if self.file_exists(datasource_parameter):
                datasource_parameter = self.__get_file_id(datasource_parameter)
            else:
                raise Exception(f"File {datasource_parameter} not found in server for the current logged user")

        # If datasource type is 2 (OLE DB), 3 (SQL Server), 4 (Oracle) or 8 (Shared Files), we just use the
        # datasource_parameter with no further validation

        # Set URL & parameters(body)
        url = f"{self.__base_url}/{API_VERSION}/integration/exports"
        body = {
            "Name": parameters.get("Name"),
            "Reference": parameters.get("Reference"),
            "Description": parameters.get("Description") if parameters.get("Description") is not None else "",
            "ExportGroupId": export_group_id,
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
            raise Exception(
                f"Error adding export {parameters.get('Name')} (Status code: {response.status_code}. Text: {response.text})")
        else:
            if self.__console_feedback: print("ok")

    def export_exists(self, reference, group_reference=None):
        """Check if export exists

            Parameters:
            reference (string): Reference of the export
            group_reference (string, optional): Reference of the group (folder) that contains the export. Omit for exports outside any group

            Returns:
            True if it exists, otherwise False
        """
        if self.__console_feedback: print(f"Checking if export exists {reference}...", end="")
        # Get exports of the informed group (or the ones outside any group)
        exports = self.__get_exports(self.__get_export_group_id(group_reference))

        # Search for desired export (and return True if found)
        for exp in exports:
            if exp['Reference'] == reference:
                if self.__console_feedback: print("yes")
                return True

        if self.__console_feedback: print("no")
        return False

    def remove_export(self, reference, group_reference=None):
        """Remove an existing export

            Parameters:
            reference (string): Reference of the export
            group_reference (string, optional): Reference of the group (folder) that contains the export. Omit for exports outside any group

            Returns:
            Nothing if export is removed or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Removing export {reference}...", end="")

        # Get export id
        export_id = self.__get_export_id(reference, group_reference)

        # Set URL
        url = f"{self.__base_url}/{API_VERSION}/integration/exports/{export_id}"

        # Make DELETE request
        response = requests.delete(url, headers=self.__get_default_headers())

        # Check response
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed");
            raise Exception(
                f"Error removing export. Error details: {get_error_message_from_response(response.content)}")
        else:
            if self.__console_feedback: print("ok");

    def execute_export(self, reference, notify_by_email, idiom_code, parameters=None, group_reference=None):
        """Execute export (this function is synchronous and will wait for the export to finish executing)

            Parameters:
            reference (string): Reference of the export
            notify_by_email (bool): True if email notification should be sent when export finishes executing, False otherwise
            idiom_code (string): Code of the idiom to be used
            parameters (optional): parameters to be used in the export
            group_reference (string, optional): Reference of the group (folder) that contains the export. Omit for exports outside any group

            Returns:
            Nothing if export is executed or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Executing export {reference}...", end="")

        # Get export id
        export_id = self.__get_export_id(reference, group_reference)

        # Get idiom id
        idiom_id = self.__get_idiom_id(idiom_code)

        # Set parameters' values (if informed)
        parameter_values = parameters if parameters is not None else []

        # Set URL & parameters
        url = f"{self.__base_url}/{API_VERSION}/integration/exports/{export_id}/execute"
        body = {"ParametersValue": parameter_values,
                "OperationDate": CorporateServer.__get_current_utc_iso8601(),
                "NotifyByEmail": notify_by_email,
                "IdiomId": idiom_id if idiom_id != -1 else self.__default_idiom_id}

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(
                f"Error calling execute export. Error details: {get_error_message_from_response(response.content)}")

        # Read operation id (that is returned in response.text)
        operation_id = response.text

        # Wait for operation to finish
        self.__wait_for_operation_to_finish(operation_id)

        if self.__console_feedback: print("ok");

    def script_group_exists(self, reference):
        """Check if script group (folder) exists

            Parameters:
            reference (string): Reference of the script group

            Returns:
            True if it exists, otherwise False
        """
        if self.__console_feedback: print(f"Checking if script group exists {reference}...", end="")
        # Get script groups
        script_groups = self.__get_script_groups()

        # Search for desired script group (and return True if found)
        for script_group in script_groups:
            if script_group['Reference'] == reference:
                if self.__console_feedback: print("yes")
                return True

        if self.__console_feedback: print("no")
        return False

    def add_script_group(self, name, reference, description):
        """Add a new script group (folder) to the selected model

            Parameters:
            name (string): Name of the script group
            reference (string): Reference of the script group
            description (string): Description of the script group

            Returns:
            Nothing if script group is created or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Adding new script group {name} ({reference})...", end="")

        # Set URL & parameters
        url = f"{self.__base_url}/{API_VERSION}/integration/script-groups"
        body = { "Name": name, "Reference": reference, "Description": description }

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check response
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error creating script group. Error details: {get_error_message_from_response(response.content)}")
        else:
            if self.__console_feedback: print("ok")

    def remove_script_group(self, reference):
        """Remove an existing script group (folder)

            Parameters:
            reference (string): Reference of the script group

            Returns:
            Nothing if script group is removed or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Removing script group {reference}...", end="")

        # Get script group id
        script_group_id = self.__get_script_group_id(reference)

        # Set URL
        url = f"{self.__base_url}/{API_VERSION}/integration/script-groups/{script_group_id}"

        # Make DELETE request
        response = requests.delete(url, headers=self.__get_default_headers())

        # Check response
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error removing script group. Error details: {get_error_message_from_response(response.content)}")
        else:
            if self.__console_feedback: print("ok")

    def add_script(self, name, reference, description, group_reference=None):
        """Add a new script

            Parameters:
            name (string): Name of the script
            reference (string): Reference of the script
            description (string): Description of the script
            group_reference (string, optional): Reference of the group (folder) where the script is created. Omit to create it outside any group

            Returns:
            Nothing if script is created or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Adding new script {name} ({reference})...", end="")

        # Get the script group id (if group_reference is informed, otherwise the script is created outside any group)
        script_group_id = self.__get_script_group_id(group_reference)

        # Set URL & parameters
        url = f"{self.__base_url}/{API_VERSION}/integration/scripts"
        body = { "Name": name, "Reference": reference, "Description": description, "ScriptGroupId": script_group_id }

        # Make GET request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check response
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")

            raise Exception(f"Error creating script. Error details: {get_error_message_from_response(response.content)}")
        else:
            if self.__console_feedback: print("ok")

    def remove_script(self, reference, group_reference=None):
        """Remove an existing script

            Parameters:
            reference (string): Reference of the script
            group_reference (string, optional): Reference of the group (folder) that contains the script. Omit for scripts outside any group

            Returns:
            Nothing if script is removed or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Removing script {reference} from model...", end="")

        # Get script id
        script_id = self.__get_script_id(reference, group_reference)

        # Set URL & parameters
        url = f"{self.__base_url}/{API_VERSION}/integration/scripts"
        params = { "ids" : script_id }

        # Make DELETE request
        response = requests.delete(url, params=params, headers=self.__get_default_headers())

        # Check response
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")

            raise Exception(f"Error removing script. Error details: {get_error_message_from_response(response.content)}")
        else:
            if self.__console_feedback: print("ok")

    def add_md_cube_to_script(self, script_reference, cube_reference, force_reprocessing, script_group_reference=None):
        """Add multidimensional cube to script

            Parameters:
            script_reference (string): Reference of the script where the cube will be added
            cube_reference (string): Reference of the cube to be added
            force_reprocessing (boolean): Indicates if the cube has to be completely reprocessing
            script_group_reference (string, optional): Reference of the group (folder) that contains the script. Omit for scripts outside any group

            Returns:
            Nothing if cube is added an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Adding multidimensional cube {cube_reference} to script {script_reference}...", end="")

        # Get script id
        script_id = self.__get_script_id(script_reference, script_group_reference)

        # Get cube id
        cube_id = self.__get_cube_id(cube_reference)

        # Set URL & parameters
        url = f"{self.__base_url}/{API_VERSION}/integration/scripts/{script_id}/operations"

        # OperationId, Name, OperationOrd and AccessRight properties are not used by the server and are set to 0 or empty string here
        body = { "Operations": [ { "OperationId": 0, "OperationType": 1, "Details": f"C={{{str(cube_id)}}} F={{{force_reprocessing}}}", "Name":  "", "OperationOrd": 0, "AccessRight": 0 } ] }

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
             if self.__console_feedback: print("failed")
             raise Exception(f"Error adding cube to script (Status code: {get_error_message_from_response(response.content)})")
        else:
            if self.__console_feedback: print("ok")

    def add_tb_cube_to_script(self, script_reference, cube_reference, processing_type, period_scenario_list=None, script_group_reference=None):
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
            script_group_reference (string, optional): Reference of the group (folder) that contains the script. Omit for scripts outside any group

            Returns:
            Nothing if cube is added an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Adding tabular cube {cube_reference} to script {script_reference}...", end="")

        # Get script id
        script_id = self.__get_script_id(script_reference, script_group_reference)

        # Get cube id
        cube_id = self.__get_cube_id(cube_reference)

        # Convert period/scenario list into an association id string separated by comma
        ps_ids = self.__get_association_list(period_scenario_list)

        # Set URL & parameters
        url = f"{self.__base_url}/{API_VERSION}/integration/scripts/{script_id}/operations"

        # OperationId, Name, OperationOrd and AccessRight properties are not used by the server and are set to 0 or empty string here
        body = { "Operations": [ { "OperationId": 0, "OperationType": 1, "Details": f"C={{{str(cube_id)}}} T={{{processing_type}}} A={{{ps_ids}}}", "Name":  "", "OperationOrd": 0, "AccessRight": 0 } ] }

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error adding cube to script. Error details: {get_error_message_from_response(response.content)}")
        else:
            if self.__console_feedback: print("ok")

    def add_export_to_script(self, script_reference, export_reference, script_group_reference=None, export_group_reference=None):
        """Add export to script

            Parameters:
            script_reference (string): Reference of the script where the export will be added
            export_reference (string): Reference of the export to be added
            script_group_reference (string, optional): Reference of the group (folder) that contains the script. Omit for scripts outside any group
            export_group_reference (string, optional): Reference of the group (folder) that contains the export. Omit for exports outside any group

            Returns:
            Nothing if export is added an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Adding export {export_reference} to script {script_reference}...", end="")

        # Get script id
        script_id = self.__get_script_id(script_reference, script_group_reference)

        # Get export id
        export_id = self.__get_export_id(export_reference, export_group_reference)

        # Set URL & parameters
        url = f"{self.__base_url}/{API_VERSION}/integration/scripts/{script_id}/operations"
        # OperationId, Name, OperationOrd and AccessRight properties are not used by the server and are set to 0 or empty string here
        body = { "Operations": [ { "OperationId": 0, "OperationType": 5, "Details": str(export_id), "Name":  "", "OperationOrd": 0, "AccessRight": 0 } ] }

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error adding export to script. Error details: {get_error_message_from_response(response.content)}")
        else:
            if self.__console_feedback: print("ok")

    def add_import_to_script(self, script_reference, import_reference, script_group_reference=None, import_group_reference=None):
        """Add import to script

            Parameters:
            script_reference (string): Reference of the script where the import will be added
            import_reference (string): Reference of the import to be added
            script_group_reference (string, optional): Reference of the group (folder) that contains the script. Omit for scripts outside any group
            import_group_reference (string, optional): Reference of the group (folder) that contains the import. Omit for imports outside any group

            Returns:
            Nothing if import is added an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Adding import {import_reference} to script {script_reference}...", end="")

        # Get script id
        script_id = self.__get_script_id(script_reference, script_group_reference)

        # Get import id
        import_id = self.__get_import_id(import_reference, import_group_reference)

        # Set URL & parameters
        url = f"{self.__base_url}/{API_VERSION}/integration/scripts/{script_id}/operations"
        # OperationId, Name, OperationOrd and AccessRight properties are not used by the server and are set to 0 or empty string here
        body = { "Operations": [ { "OperationId": 0, "OperationType": 2, "Details": str(import_id), "Name":  "", "OperationOrd": 0, "AccessRight": 0 } ] }

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error adding import to script. Error details: {get_error_message_from_response(response.content)}")
        else:
            if self.__console_feedback: print("ok")

    def add_model_calculation_to_script(self, script_reference, period_scenario_list=None, selection_when_running=False, script_group_reference=None):
        """Add calculation operation to script

        Parameters:
        script_reference (string): Reference of the script where the calculation will be added
        period_scenario_list (list): List of period_reference/scenario_reference to be calculated.
                                     One calculation operation is added for each association informed
        selection_when_running (boolean): True to leave the association to be chosen when the script is executed
                                          (the default period/scenario informed in execute_script is used).
                                          Cannot be combined with period_scenario_list
        script_group_reference (string, optional): Reference of the group (folder) that contains the script. Omit for scripts outside any group

        Returns:
        Nothing if calculation is added an Exception if it fails for any reason
        """

        # The association list and the selection when running are mutually exclusive
        if selection_when_running and period_scenario_list:
            raise Exception("Error adding calculation to script. period_scenario_list cannot be informed when selection_when_running is True")

        # Without one of them there is no association to calculate
        if not selection_when_running and not period_scenario_list:
            raise Exception("Error adding calculation to script. Inform period_scenario_list or set selection_when_running to True")

        if self.__console_feedback: print(f"Adding calculation to script...", end="")

        # Get script id
        script_id = self.__get_script_id(script_reference, script_group_reference)

        # The server reads the details of a calculation operation as a single association id, so one
        # operation is added for each association (-1 asks for the association when the script runs)
        if selection_when_running:
            association_ids = [SCRIPT_ASSOCIATION_SELECTION_WHEN_RUNNING]
        else:
            association_ids = [self.__get_association_id(item.get('PeriodReference'), item.get('ScenarioReference'))
                               for item in period_scenario_list]

        # Set URL & parameters
        url = f"{self.__base_url}/{API_VERSION}/integration/scripts/{script_id}/operations"
        # OperationId, Name, OperationOrd and AccessRight properties are not used by the server and are set to 0 or empty string here
        operations = [ { "OperationId": 0, "OperationType": 0, "Details": str(association_id), "Name":  "", "OperationOrd": 0, "AccessRight": 0 }
                       for association_id in association_ids ]
        body = { "Operations": operations }

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error adding calculation to script (Status code: {get_error_message_from_response(response.content)})")
        else:
            if self.__console_feedback: print("ok")

    def get_etl_executable_type(self, executable_id):
        """Get the type of an ETL executable declared in the server's EtlConfig.xml

            Parameters:
            executable_id (integer): Id of the executable

            Returns:
            AbmEtlType.File or AbmEtlType.Database, an Exception if the server does not declare the executable
        """

        # Search for desired executable (and return its type if found)
        for executable in self.__get_etl_executables():
            if executable['Id'] == executable_id:
                return executable['EtlType']

        # Executable not found, generate exception
        raise Exception(f"Executable '{executable_id}' not found.")

    def add_etlx_file_to_script(self, script_reference, etlx_filename, is_shared_file, script_group_reference=None, executable_id=1):
        """Add ETLX file processing to script

            Parameters:
            script_reference (string): Reference of the script where the ETLX file will be added
            etlx_filename (string): Name of the ETLX file
            is_shared_file (boolean): True if the file is in the shared file store, False if it is in the user's file store
            script_group_reference (string, optional): Reference of the group (folder) that contains the script. Omit for scripts outside any group
            executable_id (integer, optional): Id of the file executable in the server's EtlConfig.xml. Defaults to the ETL Studio package

            Returns:
            Nothing if ETLX file is added an Exception if it fails for any reason
            """

        if self.__console_feedback: print(f"Adding ETLX file {etlx_filename} to script {script_reference}...", end="")

        if is_shared_file:
            details = str(executable_id) + SEPARATOR_CONSTANT + "-1" + SEPARATOR_CONSTANT + "" + SEPARATOR_CONSTANT + "" + SEPARATOR_CONSTANT + "False" + SEPARATOR_CONSTANT + "" + SEPARATOR_CONSTANT + "" + SEPARATOR_CONSTANT + etlx_filename + SEPARATOR_CONSTANT
        else:
            # Get file id
            file_id = self.__get_file_id(etlx_filename)
            details =  str(executable_id) + SEPARATOR_CONSTANT + str(file_id) + SEPARATOR_CONSTANT + "" + SEPARATOR_CONSTANT + "" + SEPARATOR_CONSTANT + "False" + SEPARATOR_CONSTANT + "" + SEPARATOR_CONSTANT + "" + SEPARATOR_CONSTANT + "" + SEPARATOR_CONSTANT

        # Get script id
        script_id = self.__get_script_id(script_reference, script_group_reference)

        # Set URL & parameters
        url = f"{self.__base_url}/{API_VERSION}/integration/scripts/{script_id}/operations"

        # OperationId, Name, OperationOrd and AccessRight properties are not used by the server and are set to 0 or empty string here
        body = { "Operations": [ { "OperationId": 0, "OperationType": 15, "Details": details, "Name":  "", "OperationOrd": 0, "AccessRight": 0 } ] }

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error ETLX file to script. Error details: {get_error_message_from_response(response.content)}")
        else:
            if self.__console_feedback: print("ok")

    def add_etlx_database_to_script(self, script_reference, server, database, integrated_security, username, password, script_group_reference=None, executable_id=2):
        """Add ETLX database processing to script

            Parameters:
            script_reference (string): Reference of the script where the ETLX database will be added
            server (string): Server name
            database (string): Database name
            integrated_security (boolean): True for using integrated security, otherwise False
            username (string): Username
            password (string): Password
            script_group_reference (string, optional): Reference of the group (folder) that contains the script. Omit for scripts outside any group
            executable_id (integer, optional): Id of the database executable in the server's EtlConfig.xml. Defaults to the ETL Studio package

            Returns:
            Nothing if ETLX database is added an Exception if it fails for any reason
        """

        if self.__console_feedback: print(f"Adding ETLX database {database} to script {script_reference}...", end="")

        # Get script id
        script_id = self.__get_script_id(script_reference, script_group_reference)

        # Set URL & parameters
        url = f"{self.__base_url}/{API_VERSION}/integration/scripts/{script_id}/operations"
        details =  str(executable_id) + SEPARATOR_CONSTANT +  "0" + SEPARATOR_CONSTANT + server + SEPARATOR_CONSTANT +  database + SEPARATOR_CONSTANT +  str(integrated_security) + SEPARATOR_CONSTANT +  username + SEPARATOR_CONSTANT +  password + SEPARATOR_CONSTANT

        # OperationId, Name, OperationOrd and AccessRight properties are not used by the server and are set to 0 or empty string here
        body = { "Operations": [ { "OperationId": 0, "OperationType": 15, "Details": details, "Name":  "", "OperationOrd": 0, "AccessRight": 0 } ] }

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error ETLX database to script. Error details: {get_error_message_from_response(response.content)}")
        else:
            if self.__console_feedback: print("ok")

    def add_fact_to_script(self, script_reference, fact_reference, period_scenario_list=None, selection_when_running=False, script_group_reference=None):
        """Add fact to script

        Parameters:
        script_reference (string): Reference of the script where the fact will be added
        fact_reference (string): Reference  of the fact
        period_scenario_list (list): List of period_reference/scenario_reference (fact associations) to be generated.
                                     If None or empty, all associations of the fact are generated
        selection_when_running (boolean): True to leave the association to be chosen when the script is executed
                                          (the default period/scenario informed in execute_script is used).
                                          Cannot be combined with period_scenario_list
        script_group_reference (string, optional): Reference of the group (folder) that contains the script. Omit for scripts outside any group

        Returns:
        Nothing if fact is added an Exception if it fails for any reason
        """

        # The association list and the selection when running are mutually exclusive
        if selection_when_running and period_scenario_list:
            raise Exception("Error adding fact to script. period_scenario_list cannot be informed when selection_when_running is True")

        if self.__console_feedback: print(f"Adding fact {fact_reference} to script {script_reference}...", end="")

        # Get script id
        script_id = self.__get_script_id(script_reference, script_group_reference)

        # Get fact id
        fact_id = self.__get_fact_id(fact_reference, True)

        # Convert period/scenario list into an association id string separated by semicolon
        # (an empty A={} means all associations of the fact)
        if selection_when_running:
            ps_ids = str(SCRIPT_ASSOCIATION_SELECTION_WHEN_RUNNING)
        else:
            ps_ids = self.__get_association_list(period_scenario_list if period_scenario_list is not None else [])

        # Set URL & parameters
        url = f"{self.__base_url}/{API_VERSION}/integration/scripts/{script_id}/operations"

        # OperationId, Name, OperationOrd and AccessRight properties are not used by the server and are set to 0 or empty string here
        body = { "Operations": [ { "OperationId": 0, "OperationType": 9, "Details": f"F={{{str(fact_id)}}} A={{{ps_ids}}}", "Name":  "", "OperationOrd": 0, "AccessRight": 0 } ] }

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error adding fact to script. Error details: {get_error_message_from_response(response.content)}")
        else:
            if self.__console_feedback: print("ok")

    def execute_script(self, reference, notify_by_email, idiom_code, period_scenario, parameters, group_reference=None):
        """Execute a script (this function is executed synchronously ONLY if the script has 1 or more
           operations that are not exports. If all operations in the script are exports, it will
           execute asynchronously)

            Parameters:
            reference (string): Reference of the script
            notify_by_email (boolean): Indicates if an email notification should be sent to the user after the script execution
            idiom_code (string): Code of the idiom to be used
            period_scenario (string): reference (or name) of the default period/scenario (i.e.: JAN/ACTUAL). Required when the
                                      script has an operation whose association is chosen when running
            parameters (array): string array with the script parameters for possible exports/etl packages
            group_reference (string, optional): Reference of the group (folder) that contains the script. Omit for scripts outside any group

            Returns:
            Nothing if a script starts execution or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Start script {reference}...", end="")

        # Get script id
        script_id = self.__get_script_id(reference, group_reference)

        #Get idiom id
        idiom_id = self.__get_idiom_id(idiom_code)

        # Prepare default association and script parameters
        default_association_id = -1
        script_parameters = []
        script_parameter_tokens = parameters if parameters is not None else []

        # Resolve the default association from the informed period/scenario
        if period_scenario:
            default_association_id = self.__get_default_association_id(period_scenario)

        # The server rejects the execution when an operation has its association chosen when running and
        # no valid default association is informed, so check it here to give a clear message
        runtime_associations = self.__get_script_runtime_associations(script_id)
        if runtime_associations['Required']:
            allowed_associations = runtime_associations['Associations']
            if default_association_id not in [association['Id'] for association in allowed_associations]:
                allowed_list = ", ".join(f"{association['PeriodReference']}/{association['ScenarioReference']}" for association in allowed_associations)
                if period_scenario:
                    raise Exception(f"Period/scenario {period_scenario} cannot be used with script {reference}. Use one of: {allowed_list}")
                else:
                    raise Exception(f"Script {reference} requires a period/scenario to be executed. Inform one of: {allowed_list}")

        # Build ScriptParameters for each token
        if script_parameter_tokens:
            # Get script operations
            script_operation_list = self.__get_script_operations(script_id)

            if len(script_operation_list) == 0:
                raise Exception(f"Script '{reference}' does not have any operation to execute.")

            # Parse each token and match with script operations
            for token in script_parameter_tokens:
                token_params = token.split("|")
                object_id = token_params[0]
                token_params = token_params[1:]
                object_found = False
                # ETL tokens start with an executable id ("<id>;<file>" or "<id>;<server>;<database>;..."), export
                # tokens with the export reference. The separator keeps a numeric export reference an export token
                is_etl_token = ";" in object_id and object_id.split(";")[0].strip().isdigit()

                for operation in script_operation_list:
                    operation_type = operation.get("OperationType")
                    operation_id = operation.get("OperationId", operation.get("Id"))
                    operation_details = str(operation.get("Details", ""))

                    if operation_type == AbmOperationType.Export and not is_etl_token:
                        # Export operation: the details hold the export id, so read that export and match by reference
                        # (this finds the export whatever group it is in)
                        export = self.__get_export(operation_details)

                        if export['Reference'] == object_id:
                            script_parameters.append(
                                {
                                    "ScriptOperationId": operation_id,
                                    "ScriptOperationType": operation_type,
                                    "ScriptOperationDescription": "",
                                    "Parameters": token_params
                                }
                            )
                            object_found = True
                    elif operation_type == AbmOperationType.EtlPackage and is_etl_token:
                        # ETL operation: match the ETL package named in the token with the one the operation runs
                        if self.__etl_operation_matches(operation_details, object_id):
                            script_parameters.append(
                                {
                                    "ScriptOperationId": operation_id,
                                    "ScriptOperationType": operation_type,
                                    "ScriptOperationDescription": "",
                                    "Parameters": token_params
                                }
                            )
                            object_found = True
                if not object_found:
                    raise Exception(f"Parameter '{object_id}' is invalid.")

        # Set URL & parameters
        url = f"{self.__base_url}/{API_VERSION}/integration/scripts/{script_id}/execute"
        body = {
            "DefaultAssociationId": default_association_id,
            "ScriptParameters": script_parameters,
            "OperationDate": CorporateServer.__get_current_utc_iso8601(),
            "NotifyByEmail": notify_by_email,
            "IdiomId": idiom_id if idiom_id != -1 else self.__default_idiom_id
        }

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error starting script. Error details: {get_error_message_from_response(response.content)}")

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
            operations = self.__call_with_retry(
                lambda: self.__get_script_operations_in_group(group_id),
                f"Start script {reference}")

            count = len([op for op in operations if AbmOperationStatus.Scheduled <= op.get('OperationStatus') <= AbmOperationStatus.Aborting])

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
        url = f"{self.__base_url}/{API_VERSION}/analysis/facts/{fact_id}/associations"
        body = {"AssociationIds": ps_ids_int_list}

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error adding associations to false. Error details: {get_error_message_from_response(response.content)}")
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
        url = f"{self.__base_url}/{API_VERSION}/analysis/facts/{fact_id}/associations"
        body = {"AssociationIds": ps_ids_int_list}

        # Make DELETE request
        response = requests.delete(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error removing associations to false. Error details: {get_error_message_from_response(response.content)}")
        else:
            if self.__console_feedback: print("ok")

    def process_fact_associations(self, fact_reference, notify_by_email, period_scenario_list):
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
        url = f"{self.__base_url}/{API_VERSION}/analysis/facts/{fact_id}/associations/execute"
        body = { "AssociationIds": ps_ids_int_list,
                "OperationDate": self.__get_current_utc_iso8601(),
                "NotifyByEmail": notify_by_email,
                "GroupIds": [],
                "UserIds": []
            }

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error starting fact association processing. Error details: {get_error_message_from_response(response.content)}")
        else:
            if self.__console_feedback: print("ok")

    def process_fact(self, fact_reference, notify_by_email):
        """Process fact (this function is synchronous and will wait for the fact to be processed)

            Parameters:
            fact_reference (string): Reference of the fact

            Returns:
            Nothing if fact is processed or an Exception if it fails for any reason
                    """
        if self.__console_feedback: print(f"Processing fact {fact_reference}...", end="")

        # Get fact id
        fact_id = self.__get_fact_id(fact_reference)

        # Set URL & parameters
        url = f"{self.__base_url}/{API_VERSION}/analysis/facts/{fact_id}/execute"
        body = {"OperationDate": CorporateServer.__get_current_utc_iso8601(),
                "NotifyByEmail": notify_by_email,
                "GroupIds": [],
                "UserIds": []
            }

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error calling process fact. Error details: {get_error_message_from_response(response.content)}")

        # Read operation id (that is returned in response.text)
        operation_id =  response.text

        # Wait for operation to finish
        self.__wait_for_operation_to_finish(operation_id)

        if self.__console_feedback: print("ok");

    def process_regular_cube(self, reference, force_reprocessing, notify_by_email):
        """Process cube (this function is synchronous and will wait for the fact to be processed)

            Parameters:
            reference (string): Reference of the cube

            Returns:
            Nothing if cube is processed or an Exception if it fails for any reason
        """
        if self.__console_feedback: print(f"Processing cube {reference}...", end="")

        # Get cube id
        cube_id = self.__get_cube_id(reference)

        # Set URL & parameters
        url = f"{self.__base_url}/{API_VERSION}/analysis/cubes/{cube_id}/regular/execute"
        body = {"ForceReprocessing": force_reprocessing,
                "OperationDate": CorporateServer.__get_current_utc_iso8601(),
                "NotifyByEmail": notify_by_email
                }

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error processing cube. Error details: {get_error_message_from_response(response.content)}")

        # Read operation id (that is returned in response.text)
        operation_id =  response.text

        # Wait for operation to finish
        self.__wait_for_operation_to_finish(operation_id)

        if self.__console_feedback: print("ok");

    def process_tabular_cube(self, reference, cube_processing_type, notify_by_email, period_scenario_list):
        """Process cube (this function is synchronous and will wait for the fact to be processed)

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
        if self.__console_feedback: print(f"Processing cube {reference}...", end="")

        # Get cube id
        cube_id = self.__get_cube_id(reference)

        # Convert period/scenario list into an association id string separated by comma
        ps_ids = self.__get_association_list(period_scenario_list)

        # Convert ps_ids to a list if integers with the ps_ids
        ps_ids_int_list = [] if ps_ids == "" else list(map(int, ps_ids.split(";")))

        # Set URL & parameters
        url = f"{self.__base_url}/{API_VERSION}/analysis/cubes/{cube_id}/tabular/execute"
        body = {
            "CubeProcessingType": cube_processing_type,
            "AssociationIds": ps_ids_int_list,
            "OperationDate":  CorporateServer.__get_current_utc_iso8601(),
            "NotifyByEmail": notify_by_email
            }

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check if the request was successful (status code 200)
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error processing cube. Error details: {get_error_message_from_response(response.content)}")

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

        # Get association id
        ps_id = self.__get_association_id(period_reference, scenario_reference)

        # Set URL & parameters
        url = f"{self.__base_url}/{API_VERSION}/modeling/models/selected/structure/associations/{ps_id}/reset"
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
            raise Exception(f"Error resetting association. Error details: {get_error_message_from_response(response.content)}")
        else:
            if self.__console_feedback: print("ok")

    def remove_cubes_from_olap_server(self):
        """Remove all tabular and multidimensional cubes from OLAP server

            Returns:
            Nothing if cubes are removed or an Exception if it fails for any reason
        """
        if self.__console_feedback: print("Removing cubes from OLAP server...", end="")

        # Set URL
        url = f"{self.__base_url}/{API_VERSION}/analysis/cubes/olap-server"

        # Make DELETE request
        response = requests.delete(url, headers=self.__get_default_headers())

        # Check response
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")

            raise Exception(f"Error removing cubes from OLAP server. Error details: {get_error_message_from_response(response.content)}")
        else:
            if self.__console_feedback: print("ok")

    def scenario_builder(self, src_period_reference, src_scenario_reference, dst_period_reference, dst_scenario_reference, parameters=None):
        """Execute scenario builder
            Parameters:
            src_period_reference (string): Reference of the source period
            src_scenario_reference (string): Reference of the source scenario
            dst_period_reference (string): Reference of the destination period
            dst_scenario_reference (string): Reference of the destination scenario
            remove_destination_association_before_starting (bool): Recreate destination association before starting
            parameters (json): JSON with all parameters

            Returns:
            Nothing if scenario_builder succeeds
        """

        if self.__console_feedback: print("Executing scenario builder...", end="")

        # Initialized the parameters to an empty dictionary if it was not informed (None)
        if parameters is None:
            parameters = {}

        # Get association ids
        src_association_id = self.__get_association_id(src_period_reference, src_scenario_reference)
        dst_association_id = self.__get_association_id(dst_period_reference, dst_scenario_reference)

        # Set URL & parameters
        url = f"{self.__base_url}/{API_VERSION}/modeling/models/selected/create-scenario"
        body = {"SourcePeriodScenarioId": src_association_id,
                "DestinationPeriodScenarioId": dst_association_id,
                "CopyAssignments": parameters.get("CopyAssignments") if parameters.get("CopyAssignments") is not None else True,
                "IncludeDriverQuantity": parameters.get("IncludeDriverQuantity") if parameters.get("IncludeDriverQuantity") is not None else True,
                "CopyOnlyDriverId": -1,
                "CopyAttributes": parameters.get("CopyAttributes") if parameters.get("CopyAttributes") is not None else True,
                "IncludeAttributeQuantity": parameters.get("IncludeAttributeQuantity") if parameters.get("IncludeAttributeQuantity") is not None else True,
                "CopyOnlyAttributeId": -1,
                "EnteredCost": parameters.get("EnteredCost") if parameters.get("EnteredCost") is not None else True,
                "OutputQuantity": parameters.get("OutputQuantity") if parameters.get("OutputQuantity") is not None else True,
                "Revenue": parameters.get("Revenue") if parameters.get("Revenue") is not None else True,
                "AssignmentsFactor": parameters.get("AssignmentsFactor") if parameters.get("AssignmentsFactor") is not None else 1,
                "AttributesFactor": parameters.get("AttributesFactor") if parameters.get("AttributesFactor") is not None else 1,
                "EnteredCostFactor": parameters.get("EnteredCostFactor") if parameters.get("EnteredCostFactor") is not None else 1,
                "OutputQuantityFactor": parameters.get("OutputQuantityFactor") if parameters.get("OutputQuantityFactor") is not None else 1,
                "RevenueFactor": parameters.get("RevenueFactor") if parameters.get("RevenueFactor") is not None else 1,
                "OperationType": parameters.get("OperationType") if parameters.get("OperationType") is not None else 1
                }

        # Make POST request
        response = requests.post(url, json=body, headers=self.__get_default_headers())

        # Check response
        if not CorporateServer.__status_code_ok(response.status_code):
            if self.__console_feedback: print("failed")
            raise Exception(f"Error starting scenario builder. Error details: {get_error_message_from_response(response.content)}")

        # Read operation id (that is returned in response.text)
        operation_id = response.text

        # Wait for operation to finish
        self.__wait_for_operation_to_finish(operation_id)

        if self.__console_feedback: print("ok")