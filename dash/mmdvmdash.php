<html>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://ajax.googleapis.com/ajax/libs/jquery/1.10.2/jquery.min.js"></script>
<script type="text/javascript">
	var LastStamp = 0;
	var SlotStamp = [];
	var SlotState = [];

	function unixtime() {
		var d = new Date();
		return parseInt(d.getTime()/1000);
	}
	
	function unix2HMS(unixtime) {
		var u = new Date(unixtime*1000);
		return ('0' + u.getUTCHours()).slice(-2) +
			':' + ('0' + u.getUTCMinutes()).slice(-2) +
			':' + ('0' + u.getUTCSeconds()).slice(-2);
	};
	
	function unix2DMYHMS(unixtime) {
		var u = new Date(unixtime*1000);
		return ('0' + u.getUTCDate()).slice(-2) +
			'.' + ('0' + u.getUTCMonth()).slice(-2) +
			'.' + u.getUTCFullYear() +
			' ' + ('0' + u.getUTCHours()).slice(-2) +
			':' + ('0' + u.getUTCMinutes()).slice(-2) +
			':' + ('0' + u.getUTCSeconds()).slice(-2);
	};
	
	function unix2DMY(unixtime) {
		var u = new Date(unixtime*1000);
		return ('0' + u.getUTCDate()).slice(-2) +
			'.' + ('0' + u.getUTCMonth()).slice(-2) +
			'.' + u.getUTCFullYear();
	};
	
	function getdmrslot(slot,element) {
		var xmlhttp = new XMLHttpRequest();
		xmlhttp.onreadystatechange = function() {
			if (this.readyState == 4 && this.status == 200) {
				try {
					var j = JSON.parse(this.responseText);
				} catch(e) {
					$("#sitestate").html("error getting state of dmrslot "+slot);
					return;
				}
				if (j.source == 'RF') {
					$("#"+element+" > #source").html("&#9768;");
					sourcesym = "&#9768;";
				} else {
					$("#"+element+" > #source").html("&#x260D;");
					sourcesym = "&#x260D;";
				}
				$("#"+element+" > #call").text(j.call);
				$("#"+element+" > #target").text(j.target);
				if (j.loss == '' && j.ber == '') {
					$("#"+element+" > #info").html(j.duration+"<br>");
				} else {
					$("#"+element+" > #info").html(j.duration+"<br>Loss: "+j.loss+" BER: "+j.ber);
				}
				if (j.state == 'AKTIV') {
					$("#flex"+element+" > #state"+element).css('background-color','red');
					$("#flex"+element+" > #state"+element+" > span").text(j.source);
					$("#flex"+element+" > #state"+element+" > span").html(sourcesym);
					$("#flex"+element+" > #state"+element).show();
				} else {
					$("#flex"+element+" > #state"+element).hide();
				}
				$("#"+element+"time > #time").text(unix2HMS(j.stamp));
				if (j.source == 'RF') {
					refreshdmrlocalheard();
				} 
				refreshdmrlastheard();
				SlotStamp[slot] = j.stamp;
				SlotState[slot] = j.state;
			}
		};
		xmlhttp.open("GET", "mmdvmdash_tools.php?getdmrslot="+slot, true);
		xmlhttp.send();
	}
	
	function getdmrstate() {
		var xmlhttp = new XMLHttpRequest();
		xmlhttp.onreadystatechange = function() {
			if (this.readyState == 4 && this.status == 200) {
				try {
					var j = JSON.parse(this.responseText);
				} catch(e) {
					$("#sitestate").html("error getting state of dmrnetwork");
					return;
				}
				if (j.dmrmaster == 'OPEN') {
					master = 'verbunden';
				} else if (j.dmrmaster == 'CLOSED') {
					master = 'nicht verbunden';
				} else {
					master = 'unbekannt';
				}
				$("#modeDMR > div > #master").text(master);
				$("#modeDMR > div > #mastertime").text(unix2DMYHMS(j.dmrmasterstamp));
				
				if (j.reflector == '') {
					reflector = 'unbekannt';
				} else if (j.reflector == '4000' || j.reflector == 'UNLINKED') {
					reflector = 'getrennt';
				} else {
					reflector = j.reflector;
				}
				$("#modeDMR > div > #reflector").text(reflector);
				$("#modeDMR > div > #reflectortime").text(unix2DMYHMS(j.reflectorstamp));
			}
		};
		xmlhttp.open("GET", "mmdvmdash_tools.php?getdmrstate", true);
		xmlhttp.send();
	};
	
	function refreshdmrlastheard() {
		var xmlhttp = new XMLHttpRequest();
		xmlhttp.onreadystatechange = function() {
			if (this.readyState == 4 && this.status == 200) {
				try {
					var j = JSON.parse(this.responseText);
				} catch(e) {
					$("#sitestate").html("error getting dmrlastheard");
					return;
				}
				for (i = 0; i < j.length; i++) {
					zeit = unix2HMS(j[i].stamp);
					row = '<tr id="call'+j[i].call+'"> \
						<td>'+zeit+'</td> \
						<td>'+j[i].slot+'</td> \
						<td>'+j[i].source+'</td> \
						<td>'+j[i].call+'</td> \
						<td>'+j[i].target+'</td> \
						<td>'+j[i].loss+'</td> \
						<td>'+j[i].ber+'</td> \
						<td>'+j[i].duration+'</td></tr>';
					if ($('#dmrlastheard > tbody > tr#call'+j[i].call).length) {
						$('#dmrlastheard > tbody > tr#call'+j[i].call).remove();
					} else {
						$('#dmrlastheard > tbody > tr:last').remove();
					}
					$('#dmrlastheard > tbody > tr:first').before(row);
				};
			}
		};
		xmlhttp.open("GET", "mmdvmdash_tools.php?getdmrlastheard", true);
		xmlhttp.send();
	};
	
	function refreshdmrlocalheard() {
		var xmlhttp = new XMLHttpRequest();
		xmlhttp.onreadystatechange = function() {
			if (this.readyState == 4 && this.status == 200) {
				try {
					var j = JSON.parse(this.responseText);
				} catch(e) {
					$("#sitestate").html("error getting dmrlocalheard");
					return;
				}
				for (i = 0; i < j.length; i++) {
					zeit = unix2HMS(j[i].stamp);
					row = '<tr id="call'+j[i].call+'"> \
						<td>'+zeit+'</td> \
						<td>'+j[i].slot+'</td> \
						<td>'+j[i].source+'</td> \
						<td>'+j[i].call+'</td> \
						<td>'+j[i].target+'</td> \
						<td>'+j[i].ber+'</td> \
						<td>'+j[i].duration+'</td></tr>';
					if ($('#dmrlocalheard > tbody > tr#call'+j[i].call).length) {
						$('#dmrlocalheard > tbody > tr#call'+j[i].call).remove();
						console.log('delete call '+j[i].call+' from local');
					} else {
						$('#dmrlocalheard > tbody > tr:last').remove();
						console.log('delete last local');
					}
					$('#dmrlocalheard > tbody > tr:first').before(row);
				};
			}
		};
		xmlhttp.open("GET", "mmdvmdash_tools.php?getdmrlocalheard", true);
		xmlhttp.send();
	};

	function getdmrlastheard(limit) {
		if (limit === undefined) {
			limit = 1;
		} 
		var xmlhttp = new XMLHttpRequest();
		xmlhttp.onreadystatechange = function() {
			if (this.readyState == 4 && this.status == 200) {
				try {
					var j = JSON.parse(this.responseText);
					$("#dmrlastheard tbody").empty();
					console.log('clear lastheard');
				} catch(e) {
					$("#sitestate").html("error getting dmrlastheard");
					return;
				}
				for (i = 0; i < j.length; i++) {
					if (unix2DMY(j[i].stamp) == unix2DMY(unixtime())) {
						zeit = unix2HMS(j[i].stamp);
					} else {
						zeit = unix2DMYHMS(j[i].stamp);
					}
					
					row = '<tr id="call'+j[i].call+'"> \
						<td>'+zeit+'</td> \
						<td>'+j[i].slot+'</td> \
						<td>'+j[i].source+'</td> \
						<td>'+j[i].call+'</td> \
						<td>'+j[i].target+'</td> \
						<td>'+j[i].loss+'</td> \
						<td>'+j[i].ber+'</td> \
						<td>'+j[i].duration+'</td></tr>';
					$("#dmrlastheard > tbody").append(row);
				};
			}
		};
		xmlhttp.open("GET", "mmdvmdash_tools.php?getdmrlastheard="+limit, true);
		xmlhttp.send();
	};

	function getdmrlocalheard(limit) {
		if (limit === undefined) {
			limit = 1;
		} 
		var xmlhttp = new XMLHttpRequest();
		xmlhttp.onreadystatechange = function() {
			if (this.readyState == 4 && this.status == 200) {
				try {
					var j = JSON.parse(this.responseText);
					$("#dmrlocalheard tbody").empty();
					console.log('clear localheard');
				} catch(e) {
					$("#sitestate").html("error getting dmrlocalheard");
					return;
				}
				for (i = 0; i < j.length; i++) {
					if (unix2DMY(j[i].stamp) == unix2DMY(unixtime())) {
						zeit = unix2HMS(j[i].stamp);
					} else {
						zeit = unix2DMYHMS(j[i].stamp);
					}
					
					row = '<tr id="call'+j[i].call+'"> \
						<td>'+zeit+'</td> \
						<td>'+j[i].slot+'</td> \
						<td>'+j[i].source+'</td> \
						<td>'+j[i].call+'</td> \
						<td>'+j[i].target+'</td> \
						<td>'+j[i].ber+'</td> \
						<td>'+j[i].duration+'</td></tr>';
					$("#dmrlocalheard > tbody").append(row);
				};
			}
		};
		xmlhttp.open("GET", "mmdvmdash_tools.php?getdmrlocalheard="+limit, true);
		xmlhttp.send();
	};

	function checkstamp() {
		var xmlhttp = new XMLHttpRequest();
		xmlhttp.onreadystatechange = function() {
			if (this.readyState == 4 && this.status == 200) {
				try {
					var j = JSON.parse(this.responseText);
					if ($("#sitestate").html() != "") {
						console.log('reload heards');
						getdmrlastheard(10);
						getdmrlocalheard(10);
					}
					$("#sitestate").html("");
				} catch(e) {
					$("#sitestate").html("error getting timestamp");
					return;
				}
				if (j.stamp > LastStamp) {
					getdmrslot('1','dmrslot1');
					getdmrslot('2','dmrslot2');
					getdmrstate();
					LastStamp = j.stamp;
				}
			}
		};
		xmlhttp.open("GET", "mmdvmdash_tools.php?getstamp", true);
		xmlhttp.send();
		if (SlotState[2] == 'AKTIV') {
			seconds = unixtime()-SlotStamp[2];
			$("#dmrslot2 > #info").text(seconds+" seconds");
		}
		if (SlotState[1] == 'AKTIV') {
			seconds = unixtime()-SlotStamp[1];
			$("#dmrslot1 > #info").text(seconds+" seconds");
		}
	};
	
	function moredmrlastheard() {
		alert('später soll mal ein Fenster mit einer großen LastHeard aufgehen, die man sortieren/filtern kann');
	}
	function moredmrlocalheard() {
		alert('später soll mal ein Fenster mit einer großen LocalHeard aufgehen, die man sortieren/filtern kann');
	}
	function resized() {
		$('.lhtable').css('max-width',$(window).width()-50);
	}
	window.addEventListener('resize', resized);
</script>

<head>
	<link href="mmdvmdash.css" rel="stylesheet">
</head>

<body>
	<div class="flexbox dmrslot_flex">
		<div class="flexboxitem dmrmode_flexitem" id="flexmodeDMR">
			<div class="topleft corner mode"><span id="modeDMR">DMR</span></div>
			<div class="slottime">irgendwann steht hier der Master ;-)</div>
			<div id="modeDMR">
				<div>&#x260D; <span class="bold" id="master"></span> <span class="info" id="mastertime"></span></div>
				<div>&#x2607; <span class="bold" id="reflector"></span> <span class="info" id="reflectortime"></span></div>
			</div>
		</div>
		<div class="flexboxitem dmrslot_flexitem" id="flexdmrslot1">
			<div class="topleft corner slotid"><span id="slot1">1</span></div>
			<div class="corner slotstate" id="statedmrslot1"><span id="slot1">&nbsp;</span></div>
			<div class="slottime" id="dmrslot1time"><span id="time"></span></div>
			<div id="dmrslot1">
				<span id="source"></span> <span id="call"></span><br>
				&#8677; <span id="target"></span><br>
				<div class="centered" id="info"></div>
			</div>
		</div>
		<div class="flexboxitem dmrslot_flexitem" id="flexdmrslot2">
			<div class="topleft corner slotid"><span id="slot2">2</span></div>
			<div class="corner slotstate" id="statedmrslot2"><span id="slot2">&nbsp;</span></div>
			<div class="slottime" id="dmrslot2time"><span id="time"></span></div>
			<div id="dmrslot2">
				<span id="source"></span> <span id="call"></span><br>
				&#8677; <span id="target"></span><br>
				<div class="centered" id="info"></div>
			</div>
		</div>
	</div>
	<div class="flexbox">
		<div class="flexboxitem">
			<div class="topleft corner boxitemtitle"><span id="slot2">LastHeard</span></div>
			<table class="lhtable" id="dmrlastheard">
			<thead>
				<tr>
					<th>Time</th>
					<th>Slot</th>
					<th>Source</th>
					<th>Call</th>
					<th>Target</th>
					<th>Loss</th>
					<th>BER</th>
					<th>Duration</th>
				</tr>
			</thead>
			<tbody>
			</tbody>
			</table>
			<div class="boxitemmore"><span id="slot2" onclick="moredmrlastheard()">mehr ...</span></div>
		</div>
	</div>
	<div class="flexbox">
		<div class="flexboxitem">
			<div class="topleft corner boxitemtitle"><span id="slot2">LocalHeard</span></div>
			<table class="lhtable" id="dmrlocalheard">
			<thead>
				<tr>
					<th>Time</th>
					<th>Slot</th>
					<th>Source</th>
					<th>Call</th>
					<th>Target</th>
					<th>BER</th>
					<th>Duration</th>
				</tr>
			</thead>
			<tbody>
			</tbody>
			</table>
			<div class="boxitemmore"><span id="slot2" onclick="moredmrlocalheard()">mehr ...</span></div>
		</div>
	</div>
	<div id="sitestate"></div>
</body>

</html>

<script type="text/javascript">
	setInterval(function(){ checkstamp(); }, 1000);
	getdmrlastheard(10);
	getdmrlocalheard(10);
	resized();
</script>