<?php
/**
 * Application Routes
 * 
 * Defines URL routing patterns and their corresponding controllers/actions.
 */

declare(strict_types=1);

namespace App\Config;

return [
    // Public routes
    'GET /' => ['DashboardController', 'index'],
    'GET /auth/login' => ['AuthController', 'login'],
    'GET /auth/callback' => ['AuthController', 'callback'],
    'GET /auth/logout' => ['AuthController', 'logout'],
    
    // Protected routes (require authentication)
    'GET /dashboard' => ['DashboardController', 'index'],
    
    'GET /cases' => ['CaseController', 'list'],
    'GET /cases/create' => ['CaseController', 'create'],
    'POST /cases/create' => ['CaseController', 'store'],
    'GET /cases/view/{id}' => ['CaseController', 'view'],
    
    'GET /upload' => ['UploadController', 'form'],
    'POST /upload' => ['UploadController', 'upload'],
    
    'GET /jobs' => ['JobController', 'list'],
    'GET /jobs/status/{id}' => ['JobController', 'status'],
    'POST /jobs/create' => ['JobController', 'create'],
    
    'GET /results' => ['ResultsController', 'communications'],
    'GET /results/communications' => ['ResultsController', 'communications'],
    'GET /results/attachments' => ['ResultsController', 'attachments'],
    'GET /results/timeline' => ['ResultsController', 'timeline'],
    'GET /results/network' => ['ResultsController', 'network'],
    'GET /results/map' => ['ResultsController', 'map'],
    
    'GET /admin' => ['AdminController', 'settings'],
    'GET /admin/settings' => ['AdminController', 'settings'],
];
