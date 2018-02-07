<html>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://ajax.googleapis.com/ajax/libs/jquery/1.10.2/jquery.min.js"></script>
<script type="text/javascript">
	var WaitHeard = 500;
	var TimeOffset = 0;
	var LastStamp = 0;
	var LastLocalStamp = 0;
	var SlotStamp = [];
	var SlotState = [];
	var SlotActive = [];

	function getTimeOffset() {
		offset = unixtime() - '<?php echo time();?>';
		offset = (Math.round(offset/3600))*3600
		$("#offset").html(offset);
		console.log('offset: '+offset);
		return offset;
	}

	function unixtime() {
		var d = new Date();
		return parseInt((d.getTime()/1000)-(d.getTimezoneOffset()*60));
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
			'.' + ('0' + (u.getUTCMonth()+1)).slice(-2) +
			'.' + u.getUTCFullYear() +
			' ' + ('0' + u.getUTCHours()).slice(-2) +
			':' + ('0' + u.getUTCMinutes()).slice(-2) +
			':' + ('0' + u.getUTCSeconds()).slice(-2);
	};
	
	function unix2DMY(unixtime) {
		var u = new Date(unixtime*1000);
		return ('0' + u.getUTCDate()).slice(-2) +
			'.' + ('0' + (u.getUTCMonth()+1)).slice(-2) +
			'.' + u.getUTCFullYear();
	};
	
	function getdmrduplex() {
		var xmlhttp = new XMLHttpRequest();
		xmlhttp.onreadystatechange = function() {
			if (this.readyState == 4 && this.status == 200) {
				try {
					var j = JSON.parse(this.responseText);
				} catch(e) {
					$("#sitestate").html("error getting dmr duplex");
					return;
				}
				if (j.duplex == 'False') {
					duplex = 0;
				} else if (j.duplex == 'false') {
					duplex = 0;
				} else {
					duplex = 1;
				}
				if (duplex == 0) {
					$("#flexdmrslot1").hide();
				}
			}
		};
		xmlhttp.open("GET", "mmdvmdash_tools.php?getdmrduplex", true);
		xmlhttp.send();
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
				$("#"+element+"time > #time").text(unix2HMS(j.stamp+(TimeOffset)));
				if (j.source == 'RF') {
					setTimeout(refreshdmrlocalheard(), WaitHeard);
				}
				setTimeout(refreshdmrlastheard(), WaitHeard);
				SlotActive[slot] = unixtime();
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
					masteraddress = j.dmrmasteraddress;
				} else if (j.dmrmaster == 'CLOSED') {
					master = 'nicht verbunden';
					masteraddress = j.dmrmasteraddress;
				} else {
					master = 'unbekannt';
					masteraddress = 'unbekannt'
				}
				if (masteraddress == 'localhost' || masteraddress == '127.0.0.1') {
					$("#masterDMR > #masteraddress").text('DMRGateway');
				} else {
					$("#masterDMR > #masteraddress").text(masteraddress);
				}
				$("#modeDMR > div > #master").text(master);
				$("#modeDMR > div > #mastertime").text(unix2DMYHMS(j.dmrmasterstamp+(TimeOffset)));
				
				if (j.reflector == '') {
					reflector = 'unbekannt';
				} else if (j.reflector == '4000' || j.reflector == 'UNLINKED') {
					reflector = 'getrennt';
				} else {
					reflector = j.reflector;
				}
				$("#modeDMR > div > #reflector").text(reflector);
				$("#modeDMR > div > #reflectortime").text(unix2DMYHMS(j.reflectorstamp+(TimeOffset)));
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
					zeit = unix2HMS(j[i].stamp+(TimeOffset));
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
					$(row).prependTo("#dmrlastheard > tbody");
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
					zeit = unix2HMS(j[i].stamp+(TimeOffset));
					if (LastLocalStamp != j[i].stamp) {
						LastLocalStamp = j[i].stamp;
						$('#dmrlocalheard > tbody > tr#'+LastLocalStamp).remove();
						row = '<tr id="'+LastLocalStamp+'"> \
							<td>'+zeit+'</td> \
							<td>'+j[i].slot+'</td> \
							<td>'+j[i].source+'</td> \
							<td>'+j[i].call+'</td> \
							<td>'+j[i].target+'</td> \
							<td>'+j[i].ber+'</td> \
							<td>'+j[i].duration+'</td></tr>';
						
						if (($('table#dmrlocalheard tr:last').index() + 1) >= 10) {
							$('#dmrlocalheard > tbody > tr:last').remove();
						}
						$(row).prependTo("#dmrlocalheard > tbody");
					}
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
				} catch(e) {
					$("#sitestate").html("error getting dmrlastheard");
					return;
				}
				for (i = 0; i < j.length; i++) {
					if (unix2DMY(j[i].stamp+(TimeOffset)) == unix2DMY(unixtime())) {
						zeit = unix2HMS(j[i].stamp+(TimeOffset));
					} else {
						zeit = unix2DMYHMS(j[i].stamp+(TimeOffset));
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
				} catch(e) {
					$("#sitestate").html("error getting dmrlocalheard");
					return;
				}
				for (i = 0; i < j.length; i++) {
					if (unix2DMY(j[i].stamp+(TimeOffset)) == unix2DMY(unixtime())) {
						zeit = unix2HMS(j[i].stamp+(TimeOffset));
					} else {
						zeit = unix2DMYHMS(j[i].stamp+(TimeOffset));
					}
					LastLocalStamp = j[i].stamp;
					row = '<tr id="'+LastLocalStamp+'"> \
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
		$("#dblast").html(LastStamp)
		$("#stamp").html(unixtime())
		var xmlhttp = new XMLHttpRequest();
		xmlhttp.onreadystatechange = function() {
			if (this.readyState == 4 && this.status == 200) {
				try {
					var j = JSON.parse(this.responseText);
					if ($("#sitestate").html() != "") {
						getdmrlastheard(10);
						getdmrlocalheard(10);
					}
					$("#sitestate").html("");
				} catch(e) {
					$("#sitestate").html("error getting timestamp");
					return;
				}
				$("#dbstamp").html(j.stamp)
				if (j.stamp > LastStamp) {
					getdmrslot('1','dmrslot1');
					getdmrslot('2','dmrslot2');
					getdmrstate();
					LastStamp = j.stamp;
				}
			}
		};
		xmlhttp.open("GET", "mmdvmdash_tools.php?getslotstamp", true);
		xmlhttp.send();

		$("#slotstamp").html(SlotStamp[2])

		if (SlotState[2] == 'AKTIV') {
			seconds = unixtime()-SlotActive[2];
			$("#dmrslot2 > #info").text(seconds+" seconds");
		}
		if (SlotState[1] == 'AKTIV') {
			seconds = unixtime()-SlotActive[1];
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
	<title>DashBoard</title>
</head>

<body>
	<div class="flexbox dmrslot_flex">
		<div class="flexboxitem dmrmode_flexitem" id="flexmodeDMR">
			<div class="topleft corner mode"><span id="modeDMR">DMR</span></div>
			<div class="slottime" id="masterDMR"><span id="masteraddress"></span></div>
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
			<div class="topleft corner boxitemtitle"><span id="slot2">LocalHistory</span></div>
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
	<!--
	<div id="debug">
		Offset: <span id="offset"></span><br>
		NOW: <span id="stamp"></span><br>
		dbLast: <span id="dblast"></span><br>
		dbStamp: <span id="dbstamp"></span><br>
		SlotStamp: <span id="slotstamp"></span><br>
	</div>
	-->
	<div id="sitestate"></div>
</body>

</html>

<script type="text/javascript">
	TimeOffset = getTimeOffset();
	setInterval(function(){ checkstamp(); }, 999);
	getdmrduplex();
	getdmrlastheard(10);
	getdmrlocalheard(10);
	resized();
</script>
