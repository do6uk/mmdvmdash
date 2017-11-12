# mmdvmdash
Dashboard for MMDVM / MMDVMHost / DMRGateway

## Why another dashboard?
Other dashboard-solutions are parsing log- and ini-files on-the-fly from php-script out of the webserver. Multiple visitors are causing multiple threads which finaly do the same thing. This is ineffecient and is causing systemload. 
The main thing is, to do the parsing outside the webserver and prepare data for using whitin the webserver. The php-script has only to load perpared data from database and watch for new data.
Actually this dashboard is only designed to gather and display DMR-related data. 

## Features of backend (Python3-based, running from console or as daemon)
* finding last MMDVMHost-logfile (date-independed)
* follow last MMDVMHost-logfile for changes
* parsing whole logfile on statup to get latest DMR-state
* parsin ini-files for repeater-config
* writing information in sqlite3-database
* writing selected state-information in plaintext-files

## Features of frontend (php-based, running in webserver)
* display information from sqlite3-database
 * state of dmr-master
 * state of dmr-gateway (in work)
 * state of reflector
 * state of dmr-slots
 * lastheard
 * local lastheard

## Future requests
* Actually the frontend uses javascript-polling to look for new data, that will be added to the tables and displayed in the state-boxes. It is a claim to change this to websockets, to reduce data-traffic and fasten the data update in frontend.
* The latest version is designed to run backend and frontend on same machine. Later on it should be possible to use mysql optional for remotly use of back- and frontend. This would save data-traffic and resources on MMDVMHost-site. 
* controling the MMDVMHost/DMRGateway

## Requires (backend)
* Python3
* SQLite3
* MMDVMHost
* DMRGateway (optional)

## Requires (frontend)
* PHP5 (PHP7 untested)
* SQlite3
* Apache2
* JQuery
