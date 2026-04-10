<?php
/**
 * Audit Repository
 * 
 * Handles audit log data persistence.
 */

declare(strict_types=1);

namespace App\Repositories;

use App\Config\Database;
use PDO;

class AuditRepository
{
    private PDO $db;
    
    public function __construct()
    {
        $this->db = Database::getConnection();
    }
    
    /**
     * Log an audit event
     */
    public function log(string $action, int $userId, string $entityType, ?int $entityId = null, ?array $metadata = null): void
    {
        $stmt = $this->db->prepare('
            INSERT INTO audit_logs (action, user_id, entity_type, entity_id, metadata, ip_address, user_agent, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ');
        
        $stmt->execute([
            $action,
            $userId,
            $entityType,
            $entityId,
            $metadata ? json_encode($metadata) : null,
            $_SERVER['REMOTE_ADDR'] ?? null,
            $_SERVER['HTTP_USER_AGENT'] ?? null,
        ]);
    }
    
    /**
     * Get audit logs
     */
    public function getAll(int $limit = 100, int $offset = 0): array
    {
        $stmt = $this->db->prepare('
            SELECT a.*, u.name as user_name, u.email as user_email
            FROM audit_logs a
            LEFT JOIN users u ON a.user_id = u.id
            ORDER BY a.created_at DESC
            LIMIT ? OFFSET ?
        ');
        
        $stmt->execute([$limit, $offset]);
        return $stmt->fetchAll();
    }
    
    /**
     * Get audit logs for specific entity
     */
    public function getByEntity(string $entityType, int $entityId): array
    {
        $stmt = $this->db->prepare('
            SELECT a.*, u.name as user_name, u.email as user_email
            FROM audit_logs a
            LEFT JOIN users u ON a.user_id = u.id
            WHERE a.entity_type = ? AND a.entity_id = ?
            ORDER BY a.created_at DESC
        ');
        
        $stmt->execute([$entityType, $entityId]);
        return $stmt->fetchAll();
    }
}
