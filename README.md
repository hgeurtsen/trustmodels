# How to implement Trust Models using Databricks
Democode showing How to implement a trust model using Databricks.

This demo contains of a couple of notebooks:

1. The demo is based on using a simplified version of the well known AdventureWorks database using CSV file. The CSV files are available in the 'AdventureWorks Demo Files (CSV) folder in this git repo. Place the CSV files on a DBFS folder in your Databricks workspace.
1. The 'AdventureWorks Demo Import' notebook, takes the CSV files from the configured DBFS folder and creates Delta tables in Unity Catalog. At the moment, it assumes there is a default catalog named 'workspace' in UC, and the notebook creates a schema 'adventureworks' in it and Delta tables for each configured CSV file.
1. The 'Initialize Trust Scores' notebook, simply creates the 'trustmodel' schema in the 'workspace' catalog and a Delta table 'trust_scores'.
1. The 'Compute Trust Scores' notebook, loops through all Delta tables in the adventureworks schema and populates or updates the trust_scores table.

https://www.infosupport.com