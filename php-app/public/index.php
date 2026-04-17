<?php
/**
 * MxA Mobile - Front Controller
 * 
 * Entry point for all HTTP requests.
 * Routes requests to appropriate controllers based on URL patterns.
 */

declare(strict_types=1);

// Set error reporting
error_reporting(E_ALL);
ini_set('display_errors', '0');

// Define paths
define('ROOT_PATH', dirname(__DIR__));
define('APP_PATH', ROOT_PATH . '/src');
define('PUBLIC_PATH', __DIR__);
define('STORAGE_PATH', ROOT_PATH . '/storage');

// Load Composer autoloader
require_once ROOT_PATH . '/vendor/autoload.php';

// Load environment variables
$dotenv = Dotenv\Dotenv::createImmutable(ROOT_PATH);
$dotenv->load();

// Start session
session_start();

// Initialize configuration
require_once APP_PATH . '/Config/config.php';

// Get request URI and method
$requestUri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
$requestMethod = $_SERVER['REQUEST_METHOD'];

// Simple routing
try {
    // Remove leading slash
    $path = trim($requestUri, '/');
    $segments = explode('/', $path);
    
    // Default route
    if (empty($path)) {
        require_once APP_PATH . '/Controllers/DashboardController.php';
        $controller = new App\Controllers\DashboardController();
        $controller->index();
        exit;
    }
    
    // Auth routes
    if ($segments[0] === 'auth') {
        require_once APP_PATH . '/Controllers/AuthController.php';
        $controller = new App\Controllers\AuthController();
        
        if (!isset($segments[1])) {
            $controller->login();
        } elseif ($segments[1] === 'login') {
            $controller->login();
        } elseif ($segments[1] === 'callback') {
            $controller->callback();
        } elseif ($segments[1] === 'logout') {
            $controller->logout();
        } else {
            http_response_code(404);
            echo "Not Found";
        }
        exit;
    }
    
    // Check authentication for protected routes
    if (!isset($_SESSION['user_id'])) {
        header('Location: /auth/login');
        exit;
    }
    
    // Dashboard
    if ($segments[0] === 'dashboard' || $segments[0] === '') {
        require_once APP_PATH . '/Controllers/DashboardController.php';
        $controller = new App\Controllers\DashboardController();
        $controller->index();
        exit;
    }
    
    // Cases
    if ($segments[0] === 'cases') {
        require_once APP_PATH . '/Controllers/CaseController.php';
        $controller = new App\Controllers\CaseController();
        
        if (!isset($segments[1])) {
            $controller->list();
        } elseif ($segments[1] === 'create') {
            if ($requestMethod === 'GET') {
                $controller->create();
            } else {
                $controller->store();
            }
        } elseif ($segments[1] === 'view' && isset($segments[2])) {
            $controller->view((int)$segments[2]);
        } else {
            http_response_code(404);
            echo "Not Found";
        }
        exit;
    }
    
    // Upload
    if ($segments[0] === 'upload') {
        require_once APP_PATH . '/Controllers/UploadController.php';
        $controller = new App\Controllers\UploadController();
        
        if ($requestMethod === 'GET') {
            $controller->form();
        } else {
            $controller->upload();
        }
        exit;
    }
    
    // Jobs
    if ($segments[0] === 'jobs') {
        require_once APP_PATH . '/Controllers/JobController.php';
        $controller = new App\Controllers\JobController();
        
        if (!isset($segments[1])) {
            $controller->list();
        } elseif ($segments[1] === 'status' && isset($segments[2])) {
            $controller->status($segments[2]);
        } elseif ($segments[1] === 'create') {
            $controller->create();
        } else {
            http_response_code(404);
            echo "Not Found";
        }
        exit;
    }
    
    // Results
    if ($segments[0] === 'results') {
        require_once APP_PATH . '/Controllers/ResultsController.php';
        $controller = new App\Controllers\ResultsController();
        
        if (!isset($segments[1]) || $segments[1] === 'communications') {
            $controller->communications();
        } elseif ($segments[1] === 'attachments') {
            $controller->attachments();
        } elseif ($segments[1] === 'timeline') {
            $controller->timeline();
        } elseif ($segments[1] === 'network') {
            $controller->network();
        } elseif ($segments[1] === 'map') {
            $controller->map();
        } else {
            http_response_code(404);
            echo "Not Found";
        }
        exit;
    }
    
    // Admin
    if ($segments[0] === 'admin') {
        require_once APP_PATH . '/Controllers/AdminController.php';
        $controller = new App\Controllers\AdminController();
        
        if (!isset($segments[1]) || $segments[1] === 'settings') {
            $controller->settings();
        } else {
            http_response_code(404);
            echo "Not Found";
        }
        exit;
    }
    
    // API endpoints (for AJAX calls)
    if ($segments[0] === 'api') {
        header('Content-Type: application/json');
        // API routes would go here
        echo json_encode(['error' => 'API endpoint not implemented']);
        exit;
    }
    
    // 404 - Not Found
    http_response_code(404);
    echo "404 - Page Not Found";
    
} catch (Exception $e) {
    // Log error
    error_log($e->getMessage());
    
    // Show error page
    http_response_code(500);
    if ($_ENV['APP_DEBUG'] === 'true') {
        echo "<h1>Error</h1>";
        echo "<pre>" . htmlspecialchars($e->getMessage()) . "</pre>";
        echo "<pre>" . htmlspecialchars($e->getTraceAsString()) . "</pre>";
    } else {
        echo "An error occurred. Please try again later.";
    }
}
