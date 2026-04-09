<?php

declare(strict_types=1);

require_once __DIR__ . '/../src/bootstrap.php';

Auth::requireAuth();

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo 'Method not allowed';
    exit;
}

if (!isset($_FILES['evidence']) || !is_array($_FILES['evidence'])) {
    http_response_code(400);
    echo 'Evidence file is required.';
    exit;
}

$file = $_FILES['evidence'];
if ((int) ($file['error'] ?? UPLOAD_ERR_NO_FILE) !== UPLOAD_ERR_OK) {
    http_response_code(400);
    echo 'Upload failed.';
    exit;
}

$caseNo = trim((string) ($_POST['case_no'] ?? 'CASE-001'));
$selectedModels = $_POST['selected_models'] ?? ['generic'];
if (!is_array($selectedModels)) {
    $selectedModels = ['generic'];
}

$transcribeAudio = isset($_POST['transcribe_audio']);
$tmpDir = Env::get('UPLOAD_TMP_DIR', __DIR__ . '/../storage/uploads') ?? (__DIR__ . '/../storage/uploads');
if (!is_dir($tmpDir)) {
    @mkdir($tmpDir, 0775, true);
}

$sourcePath = (string) ($file['tmp_name'] ?? '');
$originalName = (string) ($file['name'] ?? 'evidence.zip');
$safeName = preg_replace('/[^A-Za-z0-9._-]/', '_', $originalName) ?: 'evidence.zip';
$localPath = rtrim($tmpDir, '/') . '/' . uniqid('upload_', true) . '_' . $safeName;

if (!move_uploaded_file($sourcePath, $localPath)) {
    http_response_code(500);
    echo 'Failed to stage upload.';
    exit;
}

$payload = [
    'requested_by' => (string) (Auth::user()['email'] ?? Auth::user()['preferred_username'] ?? 'unknown'),
    'case_no' => $caseNo,
    'transcribe_audio' => $transcribeAudio,
    'selected_models' => array_values(array_map('strval', $selectedModels)),
    'selected_modes' => [
        'whatsapp' => true,
        'texts' => true,
        'calls' => true,
        'emails' => true,
        'audio' => true,
        'photos' => true,
        'files' => true,
    ],
];

try {
    $api = new ApiClient();
    $result = $api->submitJob($payload, $localPath, $originalName);

    $jobs = $_SESSION['jobs'] ?? [];
    if (!is_array($jobs)) {
        $jobs = [];
    }

    $jobs[] = [
        'job_id' => $result['job_id'] ?? '',
        'case_no' => $caseNo,
        'status' => $result['status'] ?? 'queued',
    ];
    $_SESSION['jobs'] = $jobs;

    @unlink($localPath);
    header('Location: /status.php?job_id=' . urlencode((string) ($result['job_id'] ?? '')));
    exit;
} catch (Throwable $e) {
    app_log('Job submission failed: ' . $e->getMessage());
    @unlink($localPath);
    http_response_code(500);
    echo 'Job submission failed: ' . h($e->getMessage());
}
