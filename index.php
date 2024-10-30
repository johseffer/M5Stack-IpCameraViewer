<?php

function downloadResizeAndDisplayImage($imageUrl) {	
    // Set the appropriate header for image output
    header('Content-Type: image/jpeg');
	
	try {
    	// Download the image
		$imageData = file_get_contents($imageUrl);
		// Create the image resource from the downloaded image data
		$image = imagecreatefromstring($imageData);
		// Resize the image to 320x240 pixels
		$resizedImage = imagescale($image, 320, 240);
		// Output the resized image
		imagejpeg($resizedImage);
		
		// Free up memory by destroying the images
		imagedestroy($image);
		imagedestroy($resizedImage);
	} catch (Exception $e) {
		http_response_code(404);
    }
	if($imageData === FALSE) {
		http_response_code(404);
	} 	
}

set_error_handler(
    function ($severity, $message, $file, $line) {
        throw new ErrorException($message, $severity, $severity, $file, $line);
    }
);

$imageurl = $_GET['url'];
downloadResizeAndDisplayImage($imageurl);

restore_error_handler();
?>
