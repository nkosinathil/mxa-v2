<?php
/**
 * Case Controller
 * 
 * Manages cases/workspaces for organizing evidence and analysis results.
 */

declare(strict_types=1);

namespace App\Controllers;

use App\Repositories\CaseRepository;

class CaseController
{
    private CaseRepository $caseRepository;
    
    public function __construct()
    {
        $this->caseRepository = new CaseRepository();
    }
    
    /**
     * List all cases
     */
    public function list(): void
    {
        $cases = $this->caseRepository->getAll();
        require_once APP_PATH . '/Views/cases/list.php';
    }
    
    /**
     * Show create case form
     */
    public function create(): void
    {
        require_once APP_PATH . '/Views/cases/create.php';
    }
    
    /**
     * Store new case
     */
    public function store(): void
    {
        $caseNumber = $_POST['case_number'] ?? '';
        $caseName = $_POST['case_name'] ?? '';
        $description = $_POST['description'] ?? '';
        
        if (empty($caseNumber) || empty($caseName)) {
            $_SESSION['error'] = 'Case number and name are required';
            header('Location: /cases/create');
            exit;
        }
        
        try {
            $caseId = $this->caseRepository->create([
                'case_number' => $caseNumber,
                'case_name' => $caseName,
                'description' => $description,
                'user_id' => $_SESSION['user_id'],
                'status' => 'active',
            ]);
            
            $_SESSION['success'] = 'Case created successfully';
            header('Location: /cases/view/' . $caseId);
            exit;
            
        } catch (\Exception $e) {
            error_log('Case creation failed: ' . $e->getMessage());
            $_SESSION['error'] = 'Failed to create case';
            header('Location: /cases/create');
            exit;
        }
    }
    
    /**
     * View case details
     */
    public function view(int $id): void
    {
        $case = $this->caseRepository->findById($id);
        
        if (!$case) {
            http_response_code(404);
            echo "Case not found";
            exit;
        }
        
        require_once APP_PATH . '/Views/cases/view.php';
    }
}
