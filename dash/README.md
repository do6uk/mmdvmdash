# What is placed here?

This directory contains the files of the web-frontend. 

You can now decide where to put the frontend:
* webserver on same machine with sqlite-connection
* webserver on external machine with mysql-connection

You have to modify the file **mmdvmdash_conf.php** and edit path 
to your sqlite-database like set in mmdvm_parser.ini or make settings for mysql-connection.

If using sqlite make sure your webserver has read-access to the database-file. 
Write-access is not needed and not recommended.
