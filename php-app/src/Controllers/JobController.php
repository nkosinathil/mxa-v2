<?php
/**
 * Job Controller
 * 
 * Manages processing jobs - submission, monitoring, and status.
 */

declare(strict_types=1);

namespace App\Controllers;

use App\Services\PythonApiClient;
use App\Repositories\JobRepository;
use App\Repositories\CaseRepository;

class JobController
{
    private PythonApiClient $pythonApi;
    private JobRepository $jobRepository;
    private CaseRepository $caseRepository;
    
    public function __construct()
    {
        $this->pythonApi = new PythonApiClient();
        $this->jobRepository = new JobRepository();
        $this->caseRepository = new CaseRepository();
    }
    
    /**
     * List all jobs
     */
    public function list(): void
    {
        $jobs = $this->jobRepository->getAll();
        require_once APP_PATH . '/Views/jobs/list.php';
    }
    
    /**
     * Get job status (AJAX endpoint)
     */
    public function status(string $jobId): void
    {
        header('Content-Type: application/json');
        
        try {
            $status = $this->pythonApi->getJobStatus($jobId);
            echo json_encode($status);
        } catch (\Exception $e) {
            http_response_code(500);
            echo json_encode(['error' => $e->getMessage()]);
        }
    }
    
    /**
     * Create new processing job
     */
    public function create(): void
    {
        if ($_SERVER['REQUEST_METHOD'] === 'GET') {
            // Show job creation form
            $caseId = $_SESSION['upload_case_id'] ?? $_GET['case_id'] ?? null;
            $uploadedFiles = $_SESSION['uploaded_files'] ?? [];
            
            $case = null;
            if ($caseId) {
                $case = $this->caseRepository->findById((int)$caseId);
            }
            
            require_once APP_PATH . '/Views/jobs/create.php';
            return;
        }
        
        // Handle POST - submit job
        $caseId = $_POST['case_id'] ?? null;
        $modes = $_POST['modes'] ?? [];
        $categoryModels = $_POST['category_models'] ?? ['generic'];
        $transcribeAudio = isset($_POST['transcribe_audio']);
        
        if (!$caseId) {
            $_SESSION['error'] = 'Case ID is required';
            header('Location: /jobs/create');
            exit;
        }
        
        try {
            $case = $this->caseRepository->findById((int)$caseId);
            if (!$case) {
                throw new \Exception('Case not found');
            }
            
            // Submit job to Python API
            $jobData = [
                'case_id' => $caseId,
                'case_number' => $case['case_number'],
                'modes' => $modes,
                'category_models' => $categoryModels,
                'transcribe_audio' => $transcribeAudio,
                'user_id' => $_SESSION['user_id'],
            ];
            
            $response = $this->pythonApi->submitJob($jobData);
            
            // Store job in database
            $this->jobRepository->create([
                'job_id' => $response['job_id'],
                'case_id' => $caseId,
                'user_id' => $_SESSION['user_id'],
                'status' => 'queued',
                'config' => json_encode($jobData),
            ]);
            
            $_SESSION['success'] = 'Job submitted successfully';
            header('Location: /jobs/status/' . $response['job_id']);
            exit;
            
        } catch (\Exception $e) {
            error_log('Job submission failed: ' . $e->getMessage());
            $_SESSION['error'] = 'Failed to submit job: ' . $e->getMessage();
            header('Location: /jobs/create');
            exit;
        }
    }
}
