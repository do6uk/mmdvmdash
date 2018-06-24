<?php

function getDMRLocalHeard($limit = 1,$local = False) {
	global $db;
	if ($limit == 0 || $limit == '') {
		$sqlimit = "LIMIT 1";
	} else {
		$sqlimit = "LIMIT $limit";
	}
	if ($local) {
		$sqlocal = "WHERE source LIKE 'RF' AND state LIKE 'end'";
	} else {
		$sqlocal = "state LIKE 'end'";
	}
	$jarr = array();
	$results = $db->query("SELECT * FROM dmr_history $sqlocal ORDER BY stamp DESC ".$sqlimit);
	while ($row = $results->fetch_array()) {
		$jarr[] = array(
		"stamp" => intval($row['stamp']),
		"slot" => $row['slot'],
		"state" => $row['state'],
		"source" => $row['source'],
		"call" => $row['caller'],
		"target" => $row['target'],
		"loss" => $row['loss'],
		"ber" => $row['ber'],
		"duration" => $row['duration'],
		"rssi" => $row['rssi']);
		
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
	while ($row = $results->fetch_array()) {
		$jarr[] = array(
		"stamp" => intval($row['stamp']),
		"slot" => $row['slot'],
		"state" => $row['state'],
		"source" => $row['source'],
		"call" => $row['caller'],
		"target" => $row['target'],
		"loss" => $row['loss'],
		"ber" => $row['ber'],
		"duration" => $row['duration'],
		"rssi" => $row['rssi']);
		
	}
	return json_encode($jarr);
}

function getDMRSlot($slot) {
	global $db;
	$results = $db->query("SELECT * FROM dmr_state WHERE slot=".$slot." LIMIT 1");
	while ($row = $results->fetch_array()) {
		$j->stamp = intval($row['stamp']);
		$j->slot = $row['slot'];
		$j->state = $row['state'];
		$j->source = $row['source'];
		$j->call = $row['caller'];
		$j->target = $row['target'];
		$j->loss = $row['loss'];
		$j->ber = $row['ber'];
		$j->duration = $row['duration'];
		$j->rssi = $row['rssi'];
	}
	return json_encode($j);
}

function getDMRState() {
	global $db;
	$results = $db->query("SELECT value,stamp FROM state WHERE varname LIKE 'DMRSlot2Reflector' LIMIT 1");
	while ($row = $results->fetch_array()) {
		$j->reflectorstamp = intval($row['stamp']);
		$j->reflector = $row['value'];
	}
	$results = $db->query("SELECT value,stamp FROM state WHERE varname LIKE 'DMRMasterState' LIMIT 1");
	while ($row = $results->fetch_array()) {
		$j->dmrmasterstamp = intval($row['stamp']);
		$j->dmrmaster = $row['value'];
	}
	$results = $db->query("SELECT value FROM state WHERE varname LIKE 'DMRMasterAddress' LIMIT 1");
	while ($row = $results->fetch_array()) {
		$j->dmrmasteraddress = $row['value'];
	}
	return json_encode($j);
}

function getDMRDuplex() {
	global $db;
	$results = $db->query("SELECT value,stamp FROM state WHERE varname LIKE 'Duplex' LIMIT 1");
	$j->duplex = 'true';
	while ($row = $results->fetch_array()) {
		$j->duplexstamp = intval($row['stamp']);
		$j->duplex = $row['value'];
	}
	return json_encode($j);
}

function getDMRMaster() {
	global $db;
	$results = $db->query("SELECT value FROM state WHERE varname LIKE 'DMRMasterAddress' LIMIT 1");
	while ($row = $results->fetch_array()) {
		$j->dmrmasteraddress = $row['value'];
	}
	$results = $db->query("SELECT value FROM state WHERE varname LIKE 'DMRMasterPort' LIMIT 1");
	while ($row = $results->fetch_array()) {
		$j->dmrmasterport = $row['value'];
	}
	return json_encode($j);
}

function getStamp() {
	global $db;
	$results = $db->query("SELECT * FROM state WHERE varname LIKE 'timestamp' LIMIT 1");
	while ($row = $results->fetch_array()) {
		$j->stamp = intval($row['value']);
	}
	return json_encode($j);
}

function getGPIO() {
	global $db;
	$results = $db->query("SELECT * FROM state WHERE varname LIKE 'gpio-%'");
	$j = [];
	$laststamp = 0;
	while ($row = $results->fetch_array()) {
		$j[str_replace('-','_',$row['varname'])] = $row['value'];
		$stamp = $row['stamp'];
		if ($stamp > $laststamp) { $laststamp = $stamp; }
	}
	$j['stamp'] = intval($laststamp);
	return json_encode($j);
}

function getSlotStamp() {
	global $db;
	$results = $db->query("SELECT stamp FROM dmr_state ORDER BY stamp DESC LIMIT 1");
	while ($row = $results->fetch_array()) {
		$j->stamp = intval($row['stamp']);
	}
	return json_encode($j);
}

?>
