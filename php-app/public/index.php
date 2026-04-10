<?php

declare(strict_types=1);

require_once __DIR__ . '/../src/bootstrap.php';

Auth::requireAuth();
$user = Auth::user();
$jobs = $_SESSION['jobs'] ?? [];

?><!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MxA - Mobile Analytics Platform</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; color: #1f2937; }
    .panel { border: 1px solid #d1d5db; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
    .row { margin-bottom: 10px; }
    input[type=text], input[type=file], select { width: 100%; padding: 8px; }
    .btn { background: #111827; color: white; border: 0; padding: 10px 14px; border-radius: 6px; cursor: pointer; }
    .btn.secondary { background: #4b5563; }
    table { width: 100%; border-collapse: collapse; }
    th, td { border-bottom: 1px solid #e5e7eb; text-align: left; padding: 8px; font-size: 14px; }
  </style>
</head>
<body>
  <div class="panel">
    <h2>MxA - Mobile Analytics</h2>
    <p>Signed in as <strong><?= h((string)($user['email'] ?? $user['preferred_username'] ?? 'unknown')) ?></strong>.</p>
    <p>Environment mapping: App `192.168.1.66` | SSO `192.168.1.59` | Python `192.168.1.90`.</p>
    <a class="btn secondary" href="/logout.php" style="text-decoration:none;display:inline-block;">Sign Out</a>
  </div>

  <div class="panel">
    <h3>Submit OCR Job</h3>
    <form action="/submit.php" method="post" enctype="multipart/form-data">
      <div class="row">
        <label>Case Number</label>
        <input type="text" name="case_no" value="CASE-001" required>
      </div>
      <div class="row">
        <label>Selected Models</label>
        <select name="selected_models[]" multiple size="4">
          <option value="generic" selected>generic</option>
          <option value="banking">banking</option>
          <option value="energy">energy</option>
          <option value="procurement">procurement</option>
          <option value="scm">scm</option>
        </select>
      </div>
      <div class="row">
        <label>Evidence ZIP / Folder Archive</label>
        <input type="file" name="evidence" required>
      </div>
      <div class="row">
        <label><input type="checkbox" name="transcribe_audio" value="1"> Enable audio transcription</label>
      </div>
      <button class="btn" type="submit">Submit for Processing</button>
    </form>
  </div>

  <div class="panel">
    <h3>Recent Jobs</h3>
    <table>
      <thead><tr><th>Job ID</th><th>Case</th><th>Status</th><th>Actions</th></tr></thead>
      <tbody>
      <?php if (empty($jobs)): ?>
        <tr><td colspan="4">No jobs submitted yet.</td></tr>
      <?php else: ?>
        <?php foreach (array_reverse($jobs) as $job): ?>
          <tr>
            <td><?= h((string)($job['job_id'] ?? '')) ?></td>
            <td><?= h((string)($job['case_no'] ?? '')) ?></td>
            <td><?= h((string)($job['status'] ?? 'queued')) ?></td>
            <td><a href="/status.php?job_id=<?= urlencode((string)($job['job_id'] ?? '')) ?>">View status</a></td>
          </tr>
        <?php endforeach; ?>
      <?php endif; ?>
      </tbody>
    </table>
  </div>
</body>
</html>
