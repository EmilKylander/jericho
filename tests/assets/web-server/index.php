<?php

$uri = $_SERVER["REQUEST_URI"];
$dir = explode("/", $uri)[1];
echo file_get_contents(str_replace("/$dir/", "", $uri));