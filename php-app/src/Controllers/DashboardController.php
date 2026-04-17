<?php
/**
 * Dashboard Controller
 * 
 * Displays main dashboard with overview statistics and quick actions.
 */

declare(strict_types=1);

namespace App\Controllers;

use App\Repositories\CaseRepository;
use App\Repositories\JobRepository;

class DashboardController
{
    private CaseRepository $caseRepository;
    private JobRepository $jobRepository;
    
    public function __construct()
    {
        $this->caseRepository = new CaseRepository();
        $this->jobRepository = new JobRepository();
    }
    
    /**
     * Display dashboard
     */
    public function index(): void
    {
        // Get dashboard statistics
        $stats = [
            'total_cases' => $this->caseRepository->count(),
            'active_cases' => $this->caseRepository->countByStatus('active'),
            'total_jobs' => $this->jobRepository->count(),
            'running_jobs' => $this->jobRepository->countByStatus('processing'),
            'completed_jobs' => $this->jobRepository->countByStatus('completed'),
            'failed_jobs' => $this->jobRepository->countByStatus('failed'),
        ];
        
        // Get recent cases
        $recentCases = $this->caseRepository->getRecent(5);
        
        // Get recent jobs
        $recentJobs = $this->jobRepository->getRecent(10);
        
        // Render dashboard view
        require_once APP_PATH . '/Views/dashboard.php';
    }
}
