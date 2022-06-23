<?php

function logger($filename, $content, $mode, $useVardump) {
	// 2 different printing methods. Some data type require var_dump to print nice
	if ($useVardump == true){
		ob_start();
		var_dump($content);
		$signature = ob_get_clean();

		$fileHandle = fopen($filename, $mode) or die ("Unable to open file");
		fwrite($fileHandle, $signature);
		fclose($fileHandle);
	}
	else {
		$fileHandle = fopen($filename, $mode);
		fwrite($fh, print_r($content, true));
		fclose($fh);
	}
}

//Loop through files //Append to array //json encode array to be used in javascript
if(isset($_GET['dev'])){ $device = $_GET['dev']; }
else{ $device = 'Screens'; }
$device = ucfirst($device);
if(isset($_GET['c'])){ $client = $_GET['c']; $client = str_replace("+"," ",$client);  }
else{ $client = 'All'; }
if(isset($_GET['row'])){ $row = $_GET['row']; }
else{ $row = 1; }
if(isset($_GET['int'])){ $interval = $_GET['int']; }
else{ $interval = 5; }

$folders = scandir($device);
$fileArr=[];
$fileAspectArr=[];
if($client == "All"){
	$di = new RecursiveDirectoryIterator($device);
}
else{
	$di = new RecursiveDirectoryIterator($device."/".$client);
}

/* Looping through the files in the directory and adding them to an array. */
foreach (new RecursiveIteratorIterator($di) as $filename => $file) {
    $replace = $device."/";
    $fileName = str_replace($replace,'',$filename);
    $tokens = explode('/', $fileName);
    $fileName2 = trim(end($tokens));
    if($fileName2 != '.' && $fileName2 != '..'){
	list($width, $height, $type, $attr) = getimagesize($file);
	$aspect = $width/$height;
	array_push($fileAspectArr, $aspect);
	//echo "pushing filename: ".$fileName." to array fileArr<br/>";
	array_push($fileArr, $fileName);
    }
}

logger("uniLog.txt", $fileArr, 'w', true);

$js_array = json_encode($fileArr);
$js_aspect = json_encode($fileAspectArr);
?>
<?php
$servername = "localhost";
$username = "ntpadministrator";
$password = "N3xu5!!!";

// Create connection
$conn = new mysqli($servername, $username, $password);

// Check connection
if ($conn->connect_error) {
  die("Connection failed: " . $conn->connect_error);
}
//echo "Connected successfully";
mysqli_select_db($conn,"upilio");
$sql="select * from DeviceAndStatus";
$result = mysqli_query($conn,$sql);
$data = array();
while($sqlrow = mysqli_fetch_array($result)) {
	$data[] = $sqlrow;
	//echo "" . $sqlrow['Device'] . "    " . $sqlrow['Status'] . "<br>";
	//echo "" . $sqlrow['Status'] . "<br>";
}

// Consolidate data into multi-dimensional array
// e.g. (0, ("Path/To/Device", "Status"))
$dataConsolidated = array();
foreach ($data as $sqlrow) {
	$currentRow = array();
	array_push($currentRow, $row['Device']);
	array_push($currentRow, $row['Status']);
	array_push($dataConsolidated, $currentRow);
}

logger("dataConsolidated.txt", $dataConsolidated, 'w', true);
foreach ($dataConsolidated as $key => $value) {
    foreach ($value as $k => $v) {
        echo "<tr>";
		logger("keyVal.txt", $k, 'a', false);
		logger("keyVal.txt", $v, 'a', false);
        //echo "<td>$k</td>"; // Get index.
        //echo "<td>$v</td>"; // Get value.
        //echo "</tr>";
    }
}

?>


<html>
<head>

<style>
body{
width:100%;
font-family:Arial, Helvetica, sans-serif;
font-weight: bold;
margin:0;
background-color:white;
overflow: hidden;
}
#tile{
        display: inline-block;
}
#tile img{
        display: block;
        margin-left: auto;
        margin-right: auto;
}
</style>
<title>
</title>
<meta http-equiv="refresh" content="300">
</head>
<body style="">
<div id="header" style="width:100%;height:10%;">
<img src="../graphics/Nexus-Icon.png" style="height:100%; width:auto;float:left;"/>
<text style="padding-left:20px;font-family:Arial, Helvetica, sans-serif;font-size:48pt;">
<?php
echo $device;
?>
</text>
</div>

<div id='tileDiv' style='text-align:center;'></div>

</body>

<script type='text/javascript'>
//Image scaling based on screen display dimensions
var device = <?php echo "'$device'";?>;
var client = <?php echo "'$client'";?>;
var w = window.innerWidth;
var h = window.innerHeight;
var scale = <?php echo $row;?>;
var interval = <?php echo $interval;?> * 1000;
var aspectArr = <?php echo $js_aspect;?>;
//var scale = 3;
var tileH = h * .9 / scale;
var tileW = w * .9 / scale;
var tilePaddingLR = tileH * .05;
//Image and border attributes (79) [NOT 80 for bubble room when rounding occurs throughout calculations]
var imgH = tileH * .72;
var imgW = tileW * .72;
var imgPadding = tileH * .03;
var borderW = tileH * .02;
var borderRadius = borderW * 1.54;
//Slide calculations
var columnAmt = Math.floor(w / ((tilePaddingLR * 2) + (imgH * 16 / 9) + (imgPadding * 2) + (borderW * 2)));
var slideTileMax = scale * columnAmt;
//Buffer atributes (5x2)
var bufferH = tileH * .05;
var buffer = "<div id='buffer' style='height:"+bufferH+";'></div>";
//Nameplate (10)
var nameplateH = tileH * .05;
var nameplate = "<div id='nameplate' style='height:"+nameplateH+";'>";
//Establish string variable for creating the html tables
var tileCmd = "<div id = 'row1'><div id='rowContents1'>";
//Store php array in a javascript array
var fileArr = <?php echo $js_array;?>;
//Get array length for looping
var fileArrLength = fileArr.length;
//Array of string replacements for getting file name
var replaceArr = [device,".jpg",".JPG",".png",".PNG",".xml"];
var fileName = "";
//Store amount of rows calculated during loop for recalling
var rowCounter = 1;
//Var to store horizontal width used as tiles are being created to calculate when screen width is exceeded
var widthUsed = 0;
//String array containing the html code for each row as a separate item
var rowContentsHTMLArr = [];
//String used to create the html code that will be stored in the 'rowContentsHTMLArr' array
var html = "";
//Array of row containers used for creating the row framework
var rowArr = ["<div id = 'row1'></div>"];
//Array storing the ID's of the framework rows to be called and written to
var rowArrID = ["row1"];
//Loop through files
var k = 1;
for (var i = 0; i < fileArrLength; i++) {
	//Get width of image after scaling for calculations
	var imgW = imgH * aspectArr[i];
	//Get name of file without filepath or extension
	if(device == 'Routers' || device == 'Servers'){
		fileName = 'icon.jpg';
	}
	else{
		fileName = fileArr[i];
	}
	console.log(fileName);
	for(var x = 0; x < replaceArr.length; x++){
		fileName = fileName.replace(replaceArr[x], "");
	}
	if(device == 'Cameras'){
		fileName = fileName.replace('/', '<br/>');
	}
	else{
		fileName = fileName.split("/").pop();
	}
//	if(device != 'Cameras'){
//		clientName = fileName.split("/")[0];
//	        fileName = fileName.split("/").pop();
//	}
//	else{
//		fileName = fileName.split("/").pop();
//	}
	//Calculate width of screen used
	widthUsed = widthUsed + ((tilePaddingLR * 2) + (imgW) + (imgPadding * 2) + (borderW * 2));
	//Check if width used for tiles has exceeded the available screen width and create a new row if so
	if(widthUsed > w){
		rowCounter++;
		rowArr.push("<div id = 'row"+rowCounter+"'></div>");
		rowArrID.push("row" + [rowCounter]);
		widthUsed = 0;
		rowContentsHTMLArr.push(html);
		html = "";
	}
	else{
	html += "<div id='tile' style='height:"+tileH+"px;padding-left:"+tilePaddingLR+";padding-right:"+tilePaddingLR+";'>";
	html += buffer;
	html += "<img src='"+device+"/"+fileArr[i]+"' id='file"+k+"' style='height:"+imgH+";width:"+imgW+";padding:"+imgPadding+";border:"+borderW+"px solid green;border-radius:"+borderRadius+"px;'/>";
	html += "<div id='nameplate"+k+"' style='height:"+nameplateH+";'>"+fileName+"</div>";
	html += buffer;
	html += "</div>";
	k = k + 1;
	}
}
rowContentsHTMLArr.push(html);

//Write rows framework to html doc
var rowFramework = "";
for(var i = 0; i < rowArr.length; i++){
	rowFramework += rowArr[i];
}
document.getElementById('tileDiv').innerHTML = rowFramework;

//Check to make sure all tiles do not fit on one screen
if(slideTileMax < fileArrLength){
	//Moves contents of each row up a row (row1 contents goes to last row available)
        function changer(){
		for(var i = 0; i < rowArrID.length; i++){
			//Clear the html within the row div
			document.getElementById(rowArrID[i]).innerHTML = "";
			//Rewrite the row div's html with the code of the row below
			document.getElementById(rowArrID[i]).innerHTML = rowContentsHTMLArr[i];
		}
		//Shift the html array contents to be moved to a new div for the next iteration
		temp = rowContentsHTMLArr.shift();
		rowContentsHTMLArr.push(temp);
	}
	//Delay the function
        setInterval(changer,interval);
}
else{
	for(var i = 0; i < rowArrID.length; i++){
		//Clear the html within the row div
		document.getElementById(rowArrID[i]).innerHTML = "";
		//Rewrite the row div's html with the code of the row below
		document.getElementById(rowArrID[i]).innerHTML = rowContentsHTMLArr[i];
	}
}





























</script>



</html>
