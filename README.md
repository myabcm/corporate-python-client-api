# MyABCM Corporate Python client API


## Overview

MyABCM Corporate (v12 or newer) provides a simple and extensive REST API for end users to connect and control MyABCM from other languages.

The purpose of this package is to simplify the usage of MyABCM Corporate REST API by wrapping the most common calls in a simple to use Python class.



## A bit of history

MyABCM Corporate since its first versions, provided a REST API so users could control it from external systems/programs.

To make the use of the REST API simpler, MyABCM even released a command line utility named "MyABCM.Client.Shell" that used the provided REST API to control the basic functions of MyABCM Corporate.

The initial goal of "MyABCM.Client.Shell" was to serve as a simple example of the potential of MyABCM Corporate API but many users ended up using the utility in production to automate processes like model imports, calculation and fact/cube generation.

MyABCM.Client.Shell certainly served its purpose, but it is limited in flexibility as it does not implement the functionality of a full scripting language. Due to that limitation came the idea of implementing a Python package that could wrap around MyABCM Corporate REST API and make it easier for end users to control MyABCM Corporate from Python scripts.



## How does it work?

This package implements a single class named **CorporateServer** that implements multiple methods to control MyABCM Corporate. 

Here is a simple example of a Python script to connect to MyABCM and calculate a model:

```python
from myabcm_corporate_client_api import CorporateServer

# Create a new instance of CorporateServer class with the provided servername and credentials
corporate_server = CorporateServer("https://corporate.my-company.com/proxy", "user123", "myabcm123")

# Logon to MyABCM Corporate
corporate_server.logon()

# Select a model 
corporate_server.select_model("MY-MODEL-REFERENCE-ABC")

# Execute calculation
corporate_server.calculate_model("JAN2025", "ACTUAL" , False):

# Logoff from MyABCM Corporate
corporate_server.logoff()
```

## Methods provided by the CorporateServer class

Here are all methods exposed by the CorporateServer class. Additional details on the parameters required for each method can be obtained directly from most Python code editors as the source code of the package is fully documented using *Docstrings*.

&nbsp;  
&nbsp;  

> With the exception of **process_fact_associations**, all other methods are executed synchronously. This means if you call a method like **execute_import**, **execute_export** or any other method that executes as an operation in the server, the call will block until the operation ends.

&nbsp;  
&nbsp;  

**Logon/logoff methods**

Method | Description
--- |---
logon | Logon to the Corporate server informed in the class constructor
logoff | Logoff from the server

&nbsp;  
&nbsp;  

**Model related methods**

Method | Description
--- |---
model_exists | Check if a model exists
select_model | Select a model
remove_model | Remove a model
add_model | Add a new model
calculate_model | Calculate a specific association
reset_association | Reset an existing association
remove_cubes_from_olap_server | Remove ALL cubes from OLAP Server (tabular and SSAS)

&nbsp;  
&nbsp;  

**File store related methods**

Method | Description
--- |---
upload_file | Upload a local file to the server
download_file | Download a file from server
file_exists | Check if a file exists in the user's file store
remove_file | Remove a file from user's file store

&nbsp;  
&nbsp;  

**Import related methods**

Method | Description
--- |---
import_exists | Check if an import exists
add_import | Add a new import
remove_import | Remove an import
execute_import | Execute import

&nbsp;  
&nbsp;  


**Export related methods**

Method | Description
--- |---
add_export | Add a new export
remove_export | Remove an export
execute_export | Execute an export

&nbsp;  
&nbsp;  

**Scripts related methods**

Method | Description
--- |---
add_script | Add a new script
remove_script | Remove script
execute_script | Execute script
add_md_cube_to_script | Add a multidimensional cube to a script
add_tb_cube_to_script | Add a tabular cube to a script
add_export_to_script | Add an export to a script
add_import_to_script | Add an import to a script
add_model_calculation_to_script | Add a calculate model operation to a script
add_etlx_file_to_script | Add an ETLX package processing operation to a script
add_etlx_database_to_script | Add an ETLX(Database) package processing operation to a script
add_fact_to_script | Add a fact processing operation to a script

&nbsp;  
&nbsp;  

**Fact related methods**

Method | Description
--- |---
add_fact_associations | Add new associations to a fact
remove_fact_associations | Remove associations to a fact
process_fact_associations | Process a fact association
process_fact | Process all fact associations

&nbsp;  
&nbsp;  

**Cube related methods**

Method | Description
--- |---
process_regular_cube | Process a regular (SSAS) cube
process_tabular_cube | Process a tabular cube
