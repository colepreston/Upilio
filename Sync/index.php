<?php

if($_SERVER['REQUEST_METHOD'] == "POST") {
	// If webhook comes from Amazon AWS and is less than 15 minutes old, accept as valid
	if(reverseLookup() and checkTimestamp()) {
	//if(1) {
		// Generate html file with contents of phpinfo()
		#makePhpInfo();

		$headers = apache_request_headers(); // Get webhook headers (headers not showing up)
		$json = file_get_contents('php://input'); // Get webhook payload
		
		logger("webhook.txt", $headers, 'a', true);
		logger("webhook.txt", $json . "\n\n", 'a', false);
		
		$arr = $headers;
		$arr = $arr . "\n\n" . $json;

		$output= forward($arr);
		logger("output.txt", $output, 'a', false);
	}
} else {
	logger('invalid_requests.txt', "Invalid HTTPS request\n", 'a', false);
	logger('invalid_requests.txt', $_SERVER["REMOTE_ADDR"], 'a', false);
}

// Write $payload to stdin of python script
function forward($payload) {
	$desc = array(
		0 => array('pipe', 'r'),
		1 => array('pipe', 'w'),
		2 => array('file', 'error_output.txt', 'w')
	);

	$cmd = getConf("INDX","COMMAND");
	$p = proc_open($cmd, $desc, $pipes);	  // Spawn the process
	if(!is_resource($p)) throw new Exception("popen error");

	fwrite($pipes[0], $payload); 		  // Write the data to the child process
	fclose($pipes[0]); 			  // Close the child process
	$output = stream_get_contents($pipes[1]); // Get return value

	fclose($pipes[1]);
	proc_close($p);

	return $output;
}

function getConf($section, $record) {
	$iniArray = parse_ini_file("/etc/init/soter.ini", true);
	if ($iniArray == false)
		return false;

	$record = $iniArray[$section][$record];
	if(!isset($record)) {
		logger("Exceptions.txt", "Could not find record in configuration file.", 'w', false);
		die();
	}

	return $record;
}

function reverseLookup() {
	$shellCommand = "host " . $_SERVER['REMOTE_ADDR'];
	$comparisonString = getConf("INDX","CITRIX_HOST");

	// If webhook came from Amazon AWS, return true
	$output = shell_exec($shellCommand);

	if(strpos($output, $comparisonString) !== false){
		if($_SERVER['REMOTE_ADDR'] == getConf("INDX","ACCEPTED_ADDRESS"))
			return true;
	}
	
	// If post came from checkov, return true
	//if($_SERVER['REMOTE_ADDR'] == getConf("INDX","ACCEPTED_ADDRESS"))
	//	return true;

	return false;
}

function checkTimeStamp() {
	// placeholder until real webhooks start coming in
	// Get webhook timestamp from header
	$webhookTime = $_SERVER["HTTP-SF-WEBHOOK-TIMESTAMP"];
	//if(!is_resource($webhookTime)) return false;

	// Get current time and webhook timestamp as DateTime objects
	$currentTime = new \DateTime("now", new \DateTimeZone("UTC"));
	$webhookTime = new \DateTime($webhookTime, new \DateTimeZone("UTC"));

	// Find the time difference in minutes and convert to int
	$timeDelta = $webhookTime->diff($currentTime);
	$timeDelta = $timeDelta->format('%m');
	$timeDeltaInt = intval($timeDelta);
	logger("debug.txt", $timeDeltaInt, 'a', false);

	if ($timeDelta < getConf("INDX","WEBHOOK_TIME_TO_LIVE"))
		return true;
	
	return false;
}

function logger($filename, $content, $mode, $useVardump) {
	// 2 different printing methods. Some data types require var_dump to print nicely.
	if ($useVardump == true) {
		ob_start();
		var_dump($content);
		$signature = ob_get_clean();

		$fileHandle = fopen($filename, $mode) or die ("Unable to open file");
		fwrite($fileHandle, $signature);
		fclose($fileHandle);
	}
	else {
		$fh = fopen($filename, $mode);
		fwrite($fh, print_r($content, true));
		fclose($fh);
	}
}

function makePhpInfo() {
	// Capture output from phpinfo() in buffer and store in $phpOutput
	ob_start();
	phpinfo();
	$phpOutput = ob_get_clean();

	// $filename is a randomly generated int in range {0, 1000}
	$filename = strval(rand(0, 1000)) . ".html";

	ob_start();
	var_dump($phpOutput);
	$info = ob_get_clean();
	$fhandle = fopen($filename, 'w') or die ("Unable to open file");
	fwrite($fhandle, $info);
	fclose($fhandle);
}

?>
