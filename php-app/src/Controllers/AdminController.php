<?php
/**
 * Admin Controller
 * 
 * Administrative functions and settings management.
 */

declare(strict_types=1);

namespace App\Controllers;

use App\Repositories\UserRepository;

class AdminController
{
    private UserRepository $userRepository;
    
    public function __construct()
    {
        $this->userRepository = new UserRepository();
        
        // Check if user has admin role
        if (!in_array('admin', $_SESSION['user_roles'] ?? [])) {
            http_response_code(403);
            echo "Access Denied";
            exit;
        }
    }
    
    /**
     * Display settings page
     */
    public function settings(): void
    {
        $users = $this->userRepository->getAll();
        require_once APP_PATH . '/Views/admin/settings.php';
    }
}
