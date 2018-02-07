<?php
include('mmdvmdash_conf.php');

if ($Use_DB == 'sqlite') {
	$db = new SQLite3($SQLite_Path);
	include('mmdvmdash_sqlite.php');
} elseif ($Use_DB == 'mysql') {
	$db = new mysqli($MySQL_Host, $MySQL_User, $MySQL_Pass, $MySQL_DB, $MySQL_Port);
	include('mmdvmdash_mysql.php');
} else {
	echo "no db selected";
}

if (isset($_GET['test'])) {
	echo "TEST";
}

if (isset($_GET['getdmrslot'])) {
	$slot = $_GET['getdmrslot'];
	echo getDMRSlot($slot);
}

if (isset($_GET['getstamp'])) {
	echo getStamp();
}

if (isset($_GET['getslotstamp'])) {
	echo getSlotStamp();
}

if (isset($_GET['getdmrstate'])) {
	echo getDMRState();
}

if (isset($_GET['getdmrduplex'])) {
	echo getDMRDuplex();
}

if (isset($_GET['getdmrmaster'])) {
	echo getDMRMaster();
}

if (isset($_GET['getdmrlastheard'])) {
	$limit = $_GET['getdmrlastheard'];
	echo getDMRLastHeard($limit);
}

if (isset($_GET['getdmrlocalheard'])) {
	$limit = $_GET['getdmrlocalheard'];
	echo getDMRLocalHeard($limit, True);
}

?>
