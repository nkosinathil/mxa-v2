<?php
/**
 * Case Repository
 * 
 * Handles case/workspace data persistence and retrieval.
 */

declare(strict_types=1);

namespace App\Repositories;

use App\Config\Database;
use PDO;

class CaseRepository
{
    private PDO $db;
    
    public function __construct()
    {
        $this->db = Database::getConnection();
    }
    
    /**
     * Find case by ID
     */
    public function findById(int $id): ?array
    {
        $stmt = $this->db->prepare('SELECT * FROM cases WHERE id = ?');
        $stmt->execute([$id]);
        $case = $stmt->fetch();
        
        return $case ?: null;
    }
    
    /**
     * Create new case
     */
    public function create(array $data): int
    {
        $stmt = $this->db->prepare('
            INSERT INTO cases (case_number, case_name, description, user_id, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
        ');
        
        $stmt->execute([
            $data['case_number'],
            $data['case_name'],
            $data['description'] ?? '',
            $data['user_id'],
            $data['status'] ?? 'active',
        ]);
        
        $result = $stmt->fetch();
        return (int)$result['id'];
    }
    
    /**
     * Update case
     */
    public function update(int $id, array $data): bool
    {
        $fields = [];
        $values = [];
        
        foreach ($data as $key => $value) {
            $fields[] = "$key = ?";
            $values[] = $value;
        }
        
        $values[] = $id;
        
        $sql = 'UPDATE cases SET ' . implode(', ', $fields) . ', updated_at = CURRENT_TIMESTAMP WHERE id = ?';
        $stmt = $this->db->prepare($sql);
        
        return $stmt->execute($values);
    }
    
    /**
     * Get all cases
     */
    public function getAll(): array
    {
        $stmt = $this->db->query('
            SELECT c.*, u.name as user_name
            FROM cases c
            LEFT JOIN users u ON c.user_id = u.id
            ORDER BY c.created_at DESC
        ');
        
        return $stmt->fetchAll();
    }
    
    /**
     * Get recent cases
     */
    public function getRecent(int $limit = 10): array
    {
        $stmt = $this->db->prepare('
            SELECT c.*, u.name as user_name
            FROM cases c
            LEFT JOIN users u ON c.user_id = u.id
            ORDER BY c.created_at DESC
            LIMIT ?
        ');
        
        $stmt->execute([$limit]);
        return $stmt->fetchAll();
    }
    
    /**
     * Count total cases
     */
    public function count(): int
    {
        $stmt = $this->db->query('SELECT COUNT(*) as count FROM cases');
        $result = $stmt->fetch();
        return (int)$result['count'];
    }
    
    /**
     * Count cases by status
     */
    public function countByStatus(string $status): int
    {
        $stmt = $this->db->prepare('SELECT COUNT(*) as count FROM cases WHERE status = ?');
        $stmt->execute([$status]);
        $result = $stmt->fetch();
        return (int)$result['count'];
    }
}
