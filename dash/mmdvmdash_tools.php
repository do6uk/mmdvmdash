<?php
$db = new SQLite3('/media/ramdisk/mmdvm.db');

function getDMRLocalHeard($limit = 1,$local = False) {
	global $db;
	if ($limit == 0 || $limit == '') {
		$sqlimit = "LIMIT 1";
	} else {
		$sqlimit = "LIMIT $limit";
	}
	if ($local) {
		$sqlocal = "WHERE source LIKE 'RF'";
	} else {
		$sqlocal = "";
	}
	$jarr = array();
	$results = $db->query("SELECT * FROM dmr_localheard $sqlocal ORDER BY stamp DESC ".$sqlimit);
	while ($row = $results->fetchArray()) {
		$jarr[] = array(
		"stamp" => $row['stamp'],
		"slot" => $row['slot'],
		"state" => $row['state'],
		"source" => $row['source'],
		"call" => $row['call'],
		"target" => $row['target'],
		"loss" => $row['loss'],
		"ber" => $row['ber'],
		"duration" => $row['duration']);
		
	}
	return json_encode($jarr);
}

function getDMRLastHeard($limit = 1,$local = False) {
	global $db;
	if ($limit == 0 || $limit == '') {
		$sqlimit = "LIMIT 1";
	} else {
		$sqlimit = "LIMIT $limit";
	}
	if ($local) {
		$sqlocal = "WHERE source LIKE 'RF'";
	} else {
		$sqlocal = "";
	}
	$jarr = array();
	$results = $db->query("SELECT * FROM dmr_lastheard $sqlocal ORDER BY stamp DESC ".$sqlimit);
	while ($row = $results->fetchArray()) {
		$jarr[] = array(
		"stamp" => $row['stamp'],
		"slot" => $row['slot'],
		"state" => $row['state'],
		"source" => $row['source'],
		"call" => $row['call'],
		"target" => $row['target'],
		"loss" => $row['loss'],
		"ber" => $row['ber'],
		"duration" => $row['duration']);
		
	}
	return json_encode($jarr);
}

function getDMRSlot($slot) {
	global $db;
	$results = $db->query("SELECT * FROM dmr_state WHERE slot=".$slot." LIMIT 1");
	while ($row = $results->fetchArray()) {
		$j->stamp = $row['stamp'];
		$j->slot = $row['slot'];
		$j->state = $row['state'];
		$j->source = $row['source'];
		$j->call = $row['call'];
		$j->target = $row['target'];
		$j->loss = $row['loss'];
		$j->ber = $row['ber'];
		$j->duration = $row['duration'];
	}
	return json_encode($j);
}

function getDMRState() {
	global $db;
	$results = $db->query("SELECT value,stamp FROM state WHERE varname LIKE 'DMRSlot2Reflector' LIMIT 1");
	while ($row = $results->fetchArray()) {
		$j->reflectorstamp = $row['stamp'];
		$j->reflector = $row['value'];
	}
	$results = $db->query("SELECT value,stamp FROM state WHERE varname LIKE 'DMRMasterState' LIMIT 1");
	while ($row = $results->fetchArray()) {
		$j->dmrmasterstamp = $row['stamp'];
		$j->dmrmaster = $row['value'];
	}
	return json_encode($j);
}

function getStamp() {
	global $db;
	$results = $db->query("SELECT * FROM state WHERE varname LIKE 'timestamp' LIMIT 1");
	while ($row = $results->fetchArray()) {
		$j->stamp = $row['value'];
	}
	return json_encode($j);
}

if (isset($_GET['getdmrslot'])) {
	$slot = $_GET['getdmrslot'];
	echo getDMRSlot($slot);
}

if (isset($_GET['getstamp'])) {
	echo getStamp();
}

if (isset($_GET['getdmrstate'])) {
	echo getDMRState();
}

if (isset($_GET['getdmrlastheard'])) {
	$limit = $_GET['getdmrlastheard'];
	echo getDMRLastHeard($limit);
}

if (isset($_GET['getdmrlocalheard'])) {
	$limit = $_GET['getdmrlocalheard'];
	echo getDMRLastHeard($limit, True);
}
?>