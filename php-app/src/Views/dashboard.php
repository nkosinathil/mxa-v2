<?php require_once APP_PATH . '/Views/layouts/header.php'; ?>

<div class="dashboard">
    <h2>Dashboard</h2>
    
    <div class="stats-grid">
        <div class="stat-card">
            <h3>Total Cases</h3>
            <p class="stat-number"><?php echo $stats['total_cases']; ?></p>
        </div>
        
        <div class="stat-card">
            <h3>Active Cases</h3>
            <p class="stat-number"><?php echo $stats['active_cases']; ?></p>
        </div>
        
        <div class="stat-card">
            <h3>Running Jobs</h3>
            <p class="stat-number"><?php echo $stats['running_jobs']; ?></p>
        </div>
        
        <div class="stat-card">
            <h3>Completed Jobs</h3>
            <p class="stat-number"><?php echo $stats['completed_jobs']; ?></p>
        </div>
    </div>
    
    <div class="dashboard-sections">
        <div class="section">
            <h3>Recent Cases</h3>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Case Number</th>
                        <th>Case Name</th>
                        <th>Status</th>
                        <th>Created</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($recentCases as $case): ?>
                        <tr>
                            <td><?php echo htmlspecialchars($case['case_number']); ?></td>
                            <td><?php echo htmlspecialchars($case['case_name']); ?></td>
                            <td><span class="badge badge-<?php echo $case['status']; ?>"><?php echo $case['status']; ?></span></td>
                            <td><?php echo date('Y-m-d H:i', strtotime($case['created_at'])); ?></td>
                            <td><a href="/cases/view/<?php echo $case['id']; ?>" class="btn btn-sm">View</a></td>
                        </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h3>Recent Jobs</h3>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Job ID</th>
                        <th>Case</th>
                        <th>Status</th>
                        <th>Created</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($recentJobs as $job): ?>
                        <tr>
                            <td><?php echo substr($job['job_id'], 0, 8); ?>...</td>
                            <td><?php echo htmlspecialchars($job['case_number'] ?? 'N/A'); ?></td>
                            <td><span class="badge badge-<?php echo $job['status']; ?>"><?php echo $job['status']; ?></span></td>
                            <td><?php echo date('Y-m-d H:i', strtotime($job['created_at'])); ?></td>
                            <td><a href="/jobs/status/<?php echo $job['job_id']; ?>" class="btn btn-sm">View</a></td>
                        </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
        </div>
    </div>
    
    <div class="quick-actions">
        <h3>Quick Actions</h3>
        <div class="actions-grid">
            <a href="/cases/create" class="action-card">
                <h4>Create New Case</h4>
                <p>Start a new investigation case</p>
            </a>
            <a href="/upload" class="action-card">
                <h4>Upload Evidence</h4>
                <p>Upload files for processing</p>
            </a>
            <a href="/jobs/create" class="action-card">
                <h4>Submit Processing Job</h4>
                <p>Start evidence analysis</p>
            </a>
        </div>
    </div>
</div>

<?php require_once APP_PATH . '/Views/layouts/footer.php'; ?>
