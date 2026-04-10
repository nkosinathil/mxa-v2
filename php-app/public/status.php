<?php

declare(strict_types=1);

require_once __DIR__ . '/../src/bootstrap.php';

Auth::requireAuth();
$jobId = trim((string) ($_GET['job_id'] ?? ''));

if ($jobId === '') {
    http_response_code(400);
    echo 'Missing job_id';
    exit;
}

$status = [];
$error = null;

try {
    $api = new ApiClient();
    $status = $api->getJob($jobId);
} catch (Throwable $e) {
    $error = $e->getMessage();
}

?><!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Job Status</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; color: #1f2937; }
    .panel { border: 1px solid #d1d5db; border-radius: 8px; padding: 16px; }
    .kv { margin: 8px 0; }
  </style>
</head>
<body>
  <p><a href="/">&larr; Back to dashboard</a></p>
  <div class="panel">
    <h3>Job <?= h($jobId) ?></h3>
    <?php if ($error !== null): ?>
      <p style="color:#b91c1c">Failed to fetch job status: <?= h($error) ?></p>
    <?php else: ?>
      <div class="kv"><strong>Status:</strong> <?= h((string)($status['status'] ?? 'unknown')) ?></div>
      <div class="kv"><strong>Case:</strong> <?= h((string)($status['case_no'] ?? '')) ?></div>
      <div class="kv"><strong>Submitted by:</strong> <?= h((string)($status['requested_by'] ?? '')) ?></div>
      <div class="kv"><strong>Created:</strong> <?= h((string)($status['created_at'] ?? '')) ?></div>
      <?php if (!empty($status['result_url'])): ?>
        <div class="kv"><strong>Result:</strong> <a href="<?= h((string)$status['result_url']) ?>" target="_blank" rel="noopener">Download output bundle</a></div>
      <?php endif; ?>
      <?php if (!empty($status['summary'])): ?>
        <h4>Summary</h4>
        <pre><?= h((string)json_encode($status['summary'], JSON_PRETTY_PRINT)) ?></pre>
      <?php endif; ?>
      <?php if (!empty($status['error_message'])): ?>
        <p style="color:#b91c1c"><strong>Error:</strong> <?= h((string)$status['error_message']) ?></p>
      <?php endif; ?>
      <p><a href="/status.php?job_id=<?= urlencode($jobId) ?>">Refresh</a></p>
    <?php endif; ?>
  </div>
</body>
</html>
