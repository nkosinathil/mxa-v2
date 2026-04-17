<?php
/**
 * Authentication Controller
 * 
 * Handles Keycloak OIDC authentication flow:
 * - Login redirect to Keycloak
 * - OAuth callback handling
 * - Token exchange and validation
 * - Session management
 * - Logout
 */

declare(strict_types=1);

namespace App\Controllers;

use App\Services\KeycloakService;
use App\Repositories\UserRepository;

class AuthController
{
    private KeycloakService $keycloakService;
    private UserRepository $userRepository;
    
    public function __construct()
    {
        $this->keycloakService = new KeycloakService();
        $this->userRepository = new UserRepository();
    }
    
    /**
     * Show login page or redirect to Keycloak
     */
    public function login(): void
    {
        // If already logged in, redirect to dashboard
        if (isset($_SESSION['user_id'])) {
            header('Location: /dashboard');
            exit;
        }
        
        // Redirect to Keycloak login
        $authUrl = $this->keycloakService->getAuthorizationUrl();
        $_SESSION['oauth_state'] = $this->keycloakService->getState();
        $_SESSION['oauth_code_verifier'] = $this->keycloakService->getCodeVerifier();
        
        header('Location: ' . $authUrl);
        exit;
    }
    
    /**
     * Handle OAuth callback from Keycloak
     */
    public function callback(): void
    {
        // Verify state parameter
        if (!isset($_GET['state']) || $_GET['state'] !== ($_SESSION['oauth_state'] ?? '')) {
            die('Invalid state parameter');
        }
        
        // Check for errors
        if (isset($_GET['error'])) {
            die('Authentication error: ' . htmlspecialchars($_GET['error']));
        }
        
        // Get authorization code
        if (!isset($_GET['code'])) {
            die('No authorization code received');
        }
        
        try {
            // Exchange code for tokens
            $codeVerifier = $_SESSION['oauth_code_verifier'] ?? null;
            $tokens = $this->keycloakService->getAccessToken($_GET['code'], $codeVerifier);
            
            // Get user info from token
            $userInfo = $this->keycloakService->getUserInfo($tokens['access_token']);
            
            // Store or update user in database
            $user = $this->userRepository->findOrCreateFromKeycloak($userInfo);
            
            // Set up session
            $_SESSION['user_id'] = $user['id'];
            $_SESSION['user_email'] = $user['email'];
            $_SESSION['user_name'] = $user['name'];
            $_SESSION['user_roles'] = $user['roles'];
            $_SESSION['access_token'] = $tokens['access_token'];
            $_SESSION['refresh_token'] = $tokens['refresh_token'] ?? null;
            $_SESSION['token_expires_at'] = time() + ($tokens['expires_in'] ?? 3600);
            
            // Clear OAuth state
            unset($_SESSION['oauth_state']);
            unset($_SESSION['oauth_code_verifier']);
            
            // Log successful login
            error_log("User {$user['email']} logged in successfully");
            
            // Redirect to dashboard
            header('Location: /dashboard');
            exit;
            
        } catch (\Exception $e) {
            error_log('OAuth callback error: ' . $e->getMessage());
            die('Authentication failed. Please try again.');
        }
    }
    
    /**
     * Logout user and redirect to Keycloak logout
     */
    public function logout(): void
    {
        $userId = $_SESSION['user_id'] ?? null;
        
        // Clear session
        session_destroy();
        
        // Log logout
        if ($userId) {
            error_log("User ID {$userId} logged out");
        }
        
        // Redirect to Keycloak logout
        $logoutUrl = $this->keycloakService->getLogoutUrl();
        header('Location: ' . $logoutUrl);
        exit;
    }
}
