# How to implement Trust Models using Databricks
Democode showing How to implement a trust model using Databricks.

This demo contains of a couple of notebooks:

1. The demo is based on using a simplified version of the well known AdventureWorks database using CSV file. The CSV files are available in the 'AdventureWorks Demo Files (CSV) folder in this git repo. Place the CSV files on a DBFS folder in your Databricks workspace.
1. The 'AdventureWorks Demo Import' notebook, takes the CSV files from the configured DBFS folder and creates Delta tables in Unity Catalog. At the moment, it assumes there is a default catalog named 'workspace' in UC, and the notebook creates a schema 'adventureworks' in it and Delta tables for each configured CSV file.
1. The 'Initialize Trust Scores' notebook, simply creates the 'trustmodel' schema in the 'workspace' catalog and a Delta table 'trust_scores'.
1. The 'Compute Trust Scores' notebook, loops through all Delta tables in the adventureworks schema and populates or updates the trust_scores table.

# Demo App

The Trust Score data also comes packed with a [Streamlit](https://docs.streamlit.io/develop/api-reference) app.
In order to run the app, the Trust Score data must already be setup.  
The app can be run both locally and within Databricks. Both options will be discussed further on.

## Run the App locally

After cloning the repository, several dependencies are required to install. 

### Create virtual environment
To keep things clean, create a virtual environment.

`python -m venv venv`

Then activate the environment.

`.\venv\Scripts\activate`

### Setup environment
Install the required dependencies.

`pip install -r .\App\requirements.txt`

In order to run the app locally, the SQL Warehouse must be configured.  
Search for the connectionstring in Databricks, under *Compute > SQL Warehouses > Connection details*.  
The connectionstring typically looks like this:

`/sql/1.0/warehouses/aebf123456abcd12`

Create a new environment variable:

`DATABRICKS_WAREHOUSE_ID : aebf123456abcd12`

Now the environment should be properly setup. 
Run the app with the following command:

`streamlit run .\App\app.py`

Once initialized, the app can be viewed on http://localhost:8501

## Deploy App to Databricks
### Databricks CLI
First of all, make sure that the Databricks CLI is installed.  
This can be verified by running 

`databricks -v`

This guide is tested with v0.266.0.   
If the Databricks CLI is missing or outdated, please refer to: https://docs.databricks.com/aws/en/dev-tools/cli/install


### Create the app in Databricks

First, create the app in Databricks. Keep in mind that the Free Edition of Databricks only allows 1 app.

`databricks apps create demo-app`

This will initialize an empty app. 
In order for the app to function, a source code path must be set.   
This can be an existing (Git) folder where the App source code resides.   
If no such folder exists, it can be created by syncing the contents of the local App folder to a new Databricks folder (adjust the user accordingly):

`databricks sync --watch App/. /Workspace/Users/demo@infosupport.com/demo-app`

Once the folder is synced, the sync command can be aborted (ctrl+C on Windows).  
Now, deploy the demo-app by setting the source code path.

`databricks apps deploy demo-app --source-code-path /Workspace/Users/mark.streutker@infosupport.com/demo-app`

The app can be found under *Compute > Apps > demo-app*

### Finalizing configuration

By default, no App Resources are assigned. Press *Edit* on the demo-app to assign a SQL Warehouse.

![alt text](Images\image.png)

The key should be `sql-warehouse` to match the configuration in the app.yaml.

Finally, the app should have permissions to read data from the Trust Model.  
For production purposes, permissions should be tailored the Service Principal of the app.   
For demo purposes, a simplified configuration will suffice.

![alt text](Images\image-1.png)

### Run the app
Start the app (if it's not already running). It can be found on the following URL:
![alt text](Images\image-2.png)

https://www.infosupport.com