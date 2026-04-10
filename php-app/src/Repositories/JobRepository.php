<?php
/**
 * Job Repository
 * 
 * Handles processing job data persistence and retrieval.
 */

declare(strict_types=1);

namespace App\Repositories;

use App\Config\Database;
use PDO;

class JobRepository
{
    private PDO $db;
    
    public function __construct()
    {
        $this->db = Database::getConnection();
    }
    
    /**
     * Find job by ID
     */
    public function findById(int $id): ?array
    {
        $stmt = $this->db->prepare('SELECT * FROM processing_jobs WHERE id = ?');
        $stmt->execute([$id]);
        $job = $stmt->fetch();
        
        return $job ?: null;
    }
    
    /**
     * Find job by job_id (from Celery)
     */
    public function findByJobId(string $jobId): ?array
    {
        $stmt = $this->db->prepare('SELECT * FROM processing_jobs WHERE job_id = ?');
        $stmt->execute([$jobId]);
        $job = $stmt->fetch();
        
        return $job ?: null;
    }
    
    /**
     * Create new job
     */
    public function create(array $data): int
    {
        $stmt = $this->db->prepare('
            INSERT INTO processing_jobs (job_id, case_id, user_id, status, config, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
        ');
        
        $stmt->execute([
            $data['job_id'],
            $data['case_id'],
            $data['user_id'],
            $data['status'] ?? 'queued',
            $data['config'] ?? '{}',
        ]);
        
        $result = $stmt->fetch();
        return (int)$result['id'];
    }
    
    /**
     * Update job status
     */
    public function updateStatus(string $jobId, string $status, ?array $result = null): bool
    {
        $stmt = $this->db->prepare('
            UPDATE processing_jobs 
            SET status = ?, 
                result = ?, 
                updated_at = CURRENT_TIMESTAMP,
                completed_at = CASE WHEN ? IN (\'completed\', \'failed\') THEN CURRENT_TIMESTAMP ELSE completed_at END
            WHERE job_id = ?
        ');
        
        return $stmt->execute([
            $status,
            $result ? json_encode($result) : null,
            $status,
            $jobId,
        ]);
    }
    
    /**
     * Get all jobs
     */
    public function getAll(): array
    {
        $stmt = $this->db->query('
            SELECT j.*, c.case_number, c.case_name, u.name as user_name
            FROM processing_jobs j
            LEFT JOIN cases c ON j.case_id = c.id
            LEFT JOIN users u ON j.user_id = u.id
            ORDER BY j.created_at DESC
        ');
        
        return $stmt->fetchAll();
    }
    
    /**
     * Get recent jobs
     */
    public function getRecent(int $limit = 10): array
    {
        $stmt = $this->db->prepare('
            SELECT j.*, c.case_number, c.case_name, u.name as user_name
            FROM processing_jobs j
            LEFT JOIN cases c ON j.case_id = c.id
            LEFT JOIN users u ON j.user_id = u.id
            ORDER BY j.created_at DESC
            LIMIT ?
        ');
        
        $stmt->execute([$limit]);
        return $stmt->fetchAll();
    }
    
    /**
     * Count total jobs
     */
    public function count(): int
    {
        $stmt = $this->db->query('SELECT COUNT(*) as count FROM processing_jobs');
        $result = $stmt->fetch();
        return (int)$result['count'];
    }
    
    /**
     * Count jobs by status
     */
    public function countByStatus(string $status): int
    {
        $stmt = $this->db->prepare('SELECT COUNT(*) as count FROM processing_jobs WHERE status = ?');
        $stmt->execute([$status]);
        $result = $stmt->fetch();
        return (int)$result['count'];
    }
}
