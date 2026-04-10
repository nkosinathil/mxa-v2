<?php
/**
 * User Repository
 * 
 * Handles user data persistence and retrieval.
 */

declare(strict_types=1);

namespace App\Repositories;

use App\Config\Database;
use PDO;

class UserRepository
{
    private PDO $db;
    
    public function __construct()
    {
        $this->db = Database::getConnection();
    }
    
    /**
     * Find user by ID
     */
    public function findById(int $id): ?array
    {
        $stmt = $this->db->prepare('SELECT * FROM users WHERE id = ?');
        $stmt->execute([$id]);
        $user = $stmt->fetch();
        
        return $user ?: null;
    }
    
    /**
     * Find user by Keycloak sub (subject identifier)
     */
    public function findByKeycloakSub(string $sub): ?array
    {
        $stmt = $this->db->prepare('SELECT * FROM users WHERE keycloak_sub = ?');
        $stmt->execute([$sub]);
        $user = $stmt->fetch();
        
        return $user ?: null;
    }
    
    /**
     * Find or create user from Keycloak user info
     */
    public function findOrCreateFromKeycloak(array $userInfo): array
    {
        $sub = $userInfo['sub'] ?? '';
        $email = $userInfo['email'] ?? '';
        $name = $userInfo['name'] ?? $userInfo['preferred_username'] ?? '';
        $roles = $userInfo['realm_access']['roles'] ?? [];
        
        // Try to find existing user
        $user = $this->findByKeycloakSub($sub);
        
        if ($user) {
            // Update last login
            $stmt = $this->db->prepare('
                UPDATE users 
                SET last_login_at = CURRENT_TIMESTAMP,
                    email = ?,
                    name = ?
                WHERE id = ?
            ');
            $stmt->execute([$email, $name, $user['id']]);
            
            return $user;
        }
        
        // Create new user
        $stmt = $this->db->prepare('
            INSERT INTO users (keycloak_sub, email, name, roles, created_at, last_login_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id, keycloak_sub, email, name, roles, created_at
        ');
        
        $stmt->execute([$sub, $email, $name, json_encode($roles)]);
        $user = $stmt->fetch();
        
        if ($user && isset($user['roles'])) {
            $user['roles'] = json_decode($user['roles'], true);
        }
        
        return $user;
    }
    
    /**
     * Get all users
     */
    public function getAll(): array
    {
        $stmt = $this->db->query('
            SELECT id, email, name, created_at, last_login_at
            FROM users
            ORDER BY created_at DESC
        ');
        
        return $stmt->fetchAll();
    }
}
