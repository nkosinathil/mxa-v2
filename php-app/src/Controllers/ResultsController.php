<?php
/**
 * Results Controller
 * 
 * Displays analysis results - communications, attachments, visualizations.
 */

declare(strict_types=1);

namespace App\Controllers;

use App\Services\PythonApiClient;
use App\Repositories\CaseRepository;

class ResultsController
{
    private PythonApiClient $pythonApi;
    private CaseRepository $caseRepository;
    
    public function __construct()
    {
        $this->pythonApi = new PythonApiClient();
        $this->caseRepository = new CaseRepository();
    }
    
    /**
     * Display communications results
     */
    public function communications(): void
    {
        $caseId = $_GET['case_id'] ?? null;
        $filters = $_GET['filters'] ?? [];
        
        if (!$caseId) {
            $_SESSION['error'] = 'Case ID is required';
            header('Location: /cases');
            exit;
        }
        
        try {
            $case = $this->caseRepository->findById((int)$caseId);
            $results = $this->pythonApi->getCommunications($caseId, $filters);
            
            require_once APP_PATH . '/Views/results/communications.php';
        } catch (\Exception $e) {
            $_SESSION['error'] = 'Failed to load results';
            header('Location: /cases/view/' . $caseId);
            exit;
        }
    }
    
    /**
     * Display attachments results
     */
    public function attachments(): void
    {
        $caseId = $_GET['case_id'] ?? null;
        
        if (!$caseId) {
            $_SESSION['error'] = 'Case ID is required';
            header('Location: /cases');
            exit;
        }
        
        try {
            $case = $this->caseRepository->findById((int)$caseId);
            $results = $this->pythonApi->getAttachments($caseId);
            
            require_once APP_PATH . '/Views/results/attachments.php';
        } catch (\Exception $e) {
            $_SESSION['error'] = 'Failed to load results';
            header('Location: /cases/view/' . $caseId);
            exit;
        }
    }
    
    /**
     * Display timeline view
     */
    public function timeline(): void
    {
        $caseId = $_GET['case_id'] ?? null;
        
        if (!$caseId) {
            $_SESSION['error'] = 'Case ID is required';
            header('Location: /cases');
            exit;
        }
        
        try {
            $case = $this->caseRepository->findById((int)$caseId);
            $timeline = $this->pythonApi->getTimeline($caseId);
            
            require_once APP_PATH . '/Views/results/timeline.php';
        } catch (\Exception $e) {
            $_SESSION['error'] = 'Failed to load timeline';
            header('Location: /cases/view/' . $caseId);
            exit;
        }
    }
    
    /**
     * Display network visualization
     */
    public function network(): void
    {
        $caseId = $_GET['case_id'] ?? null;
        
        if (!$caseId) {
            $_SESSION['error'] = 'Case ID is required';
            header('Location: /cases');
            exit;
        }
        
        try {
            $case = $this->caseRepository->findById((int)$caseId);
            $network = $this->pythonApi->getNetworkData($caseId);
            
            require_once APP_PATH . '/Views/results/network.php';
        } catch (\Exception $e) {
            $_SESSION['error'] = 'Failed to load network';
            header('Location: /cases/view/' . $caseId);
            exit;
        }
    }
    
    /**
     * Display GPS map
     */
    public function map(): void
    {
        $caseId = $_GET['case_id'] ?? null;
        
        if (!$caseId) {
            $_SESSION['error'] = 'Case ID is required';
            header('Location: /cases');
            exit;
        }
        
        try {
            $case = $this->caseRepository->findById((int)$caseId);
            $gpsData = $this->pythonApi->getGPSData($caseId);
            
            require_once APP_PATH . '/Views/results/map.php';
        } catch (\Exception $e) {
            $_SESSION['error'] = 'Failed to load map';
            header('Location: /cases/view/' . $caseId);
            exit;
        }
    }
}
