# mmdvmdash
Dashboard for MMDVM / MMDVMHost / DMRGateway

## Why another dashboard?
Other dashboard-solutions are parsing log- and ini-files on-the-fly from php-script out of the webserver. Multiple visitors are causing multiple threads which finaly do the same thing. This is ineffecient and is causing systemload. 
The main thing is, to do the parsing outside the webserver and prepare data for using within the webserver. The php-script has only to load perpared data from database and watch for new data.
Actually this dashboard is only designed to gather and display DMR-related data. 

## Features of backend (Python3-based, running from console or as daemon)
* find last MMDVMHost-logfile (date-independed)
* follow last MMDVMHost-logfile for changes
* parse whole logfile on statup to get latest DMR-state
* parse ini-files for repeater-config
* write information in sqlite3-database
* write information in mysql-database (directly or as mirror of sqlite)
* write selected state-information in plaintext-files

## Features of frontend (php-based, running in webserver)
* display information from sqlite3 or mysql-database
 * state of dmr-master-connection 
 * state of dmr-gateway (in work)
 * state of reflector
 * state of dmr-slots
 * lastheard (displays last qso of an call/dmrid)
 * local history (displays last qsos on RF - multiple per call/dmrid)

## Usage of mysql
The latest version is designed to run backend and frontend on same or different machine. 
You can put web-frontend and mysql-database on external server and setup backend to store 
data in sqlite and mysql. In this variant you minimize traffic of the repeater.
This is fine for repeaters using cellular-connections with limited bandwidth.
For cellular-connections use Mirror-Option in mysql-section.

## Future requests
* parse DMRGateway-config
* parse DMRGateway-logs for connection-state
* control the MMDVMHost/DMRGateway (restart)

## Requires (backend)
* Python3
* SQLite3
* MMDVMHost
* MySQL Python3-connector (optional)
* DMRGateway (optional)

## Requires (frontend)
* PHP5 (PHP7 untested)
* SQlite3
* Apache2
* JQuery
* MySQL (optional)
