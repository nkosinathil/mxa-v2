<?php
/**
 * Upload Controller
 * 
 * Handles file uploads to MinIO for processing.
 */

declare(strict_types=1);

namespace App\Controllers;

use App\Services\MinioService;
use App\Repositories\CaseRepository;

class UploadController
{
    private MinioService $minioService;
    private CaseRepository $caseRepository;
    
    public function __construct()
    {
        $this->minioService = new MinioService();
        $this->caseRepository = new CaseRepository();
    }
    
    /**
     * Show upload form
     */
    public function form(): void
    {
        $cases = $this->caseRepository->getAll();
        require_once APP_PATH . '/Views/upload/form.php';
    }
    
    /**
     * Handle file upload
     */
    public function upload(): void
    {
        $caseId = $_POST['case_id'] ?? null;
        
        if (!$caseId) {
            $_SESSION['error'] = 'Please select a case';
            header('Location: /upload');
            exit;
        }
        
        if (!isset($_FILES['files'])) {
            $_SESSION['error'] = 'No files uploaded';
            header('Location: /upload');
            exit;
        }
        
        try {
            $case = $this->caseRepository->findById((int)$caseId);
            if (!$case) {
                throw new \Exception('Case not found');
            }
            
            $uploadedFiles = [];
            $files = $_FILES['files'];
            
            // Handle multiple file upload
            $fileCount = is_array($files['name']) ? count($files['name']) : 1;
            
            for ($i = 0; $i < $fileCount; $i++) {
                $fileName = is_array($files['name']) ? $files['name'][$i] : $files['name'];
                $tmpPath = is_array($files['tmp_name']) ? $files['tmp_name'][$i] : $files['tmp_name'];
                $fileSize = is_array($files['size']) ? $files['size'][$i] : $files['size'];
                
                // Upload to MinIO
                $objectName = sprintf(
                    'cases/%s/input/%s/%s',
                    $case['case_number'],
                    date('Y-m-d-His'),
                    $fileName
                );
                
                $this->minioService->uploadFile(
                    $tmpPath,
                    $objectName,
                    'input'
                );
                
                $uploadedFiles[] = [
                    'name' => $fileName,
                    'size' => $fileSize,
                    'object_name' => $objectName,
                ];
            }
            
            $_SESSION['success'] = count($uploadedFiles) . ' file(s) uploaded successfully';
            $_SESSION['uploaded_files'] = $uploadedFiles;
            $_SESSION['upload_case_id'] = $caseId;
            
            header('Location: /jobs/create');
            exit;
            
        } catch (\Exception $e) {
            error_log('Upload failed: ' . $e->getMessage());
            $_SESSION['error'] = 'Upload failed: ' . $e->getMessage();
            header('Location: /upload');
            exit;
        }
    }
}
