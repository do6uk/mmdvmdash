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
* state of dmr-gateway (work in progress)
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

## Installation (RaspberryPi 2/3)
1. Make sure to clone into /opt/ folder  
2. Install the MySQL Python3-connector (optional)  
sudo apt-get -y install python3-mysql.connector  
3. If you're using Debian Stretch and want php5 :  
sudo nano /etc/apt/sources.list  
#add the line bellow to the end of document and save  
deb http://mirrordirector.raspbian.org/raspbian/ jessie main contrib non-free rpi  
apt-get update  
apt-get -y install php5 php5-curl php5-cli php5-cgi php5-mysql php5-gd php5-sqlite  
4. Tweak the mmdvm_parser_example.ini and mmdvmdash_conf_example.php files to match your data and paths  
5. Copy the /opt/mmdvmdash/dash folder to your web server root (usually /var/www/html)  
6. Navigate to /opt/mmdvmdash and start the script using :  
sudo python3 ./mmdvm_parser.py  
7. (optional) To install the script as a service, execute the following copy the mmdvmdash.service and mmdvmdash.service from /opt/mmdvmdash to /lib/systemd/system and execute :  
sudo systemctl daemon-reload  
sudo systemctl enable mmdvmdash.service  
sudo systemctl start mmdvmdash.service  
8. (optional) Run 'sudo screen -R MMDVMDash' to see the output of the script  


