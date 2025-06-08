<?php
// upload.php
header('Content-Type: application/json');

$targetDir ='/var/www/html/docs';
if (!is_dir($targetDir) && !mkdir($targetDir, 0755, true)) {
    http_response_code(500);
    exit(json_encode([
        'status'=>'error',
        'message'=>'Could not create docs directory.'
    ]));
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    exit(json_encode([
        'status'=>'error',
        'message'=>'Use POST to upload.'
    ]));
}

if (!isset($_FILES['file']) || $_FILES['file']['error'] !== UPLOAD_ERR_OK) {
    http_response_code(400);
    exit(json_encode([
        'status'=>'error',
        'message'=>'Upload error or no file sent.'
    ]));
}

// grab original name & extension
$origName = basename($_FILES['file']['name']);
$base     = pathinfo($origName, PATHINFO_FILENAME);
$ext      = pathinfo($origName, PATHINFO_EXTENSION);

// sanitize + timestamp
$safeBase = preg_replace('/[^A-Za-z0-9_\-]/', '_', $base);
$newName  = $safeBase . '_' . time() . '.' . $ext;
$dest     = $targetDir . '/' . $newName;

// move it
if (!move_uploaded_file($_FILES['file']['tmp_name'], $dest)) {
    http_response_code(500);
    exit(json_encode([
        'status'=>'error',
        'message'=>'Failed to save uploaded file.'
    ]));
}

// pull the page count we sent (PDF-count or default=1)
$pageCount = isset($_POST['pageCount']) ? (int)$_POST['pageCount'] : 1;

echo json_encode([
    'status'    => 'success',
    'filename'  => $newName,
    'pageCount' => $pageCount
]);
