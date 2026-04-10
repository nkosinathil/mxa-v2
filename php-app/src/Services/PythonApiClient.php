<?php
/**
 * Python API Client
 * 
 * HTTP client for communicating with the Python FastAPI backend.
 */

declare(strict_types=1);

namespace App\Services;

use App\Config\Config;
use GuzzleHttp\Client;

class PythonApiClient
{
    private Client $client;
    private string $baseUrl;
    
    public function __construct()
    {
        $this->baseUrl = Config::get('python_api.url');
        $this->client = new Client([
            'base_uri' => $this->baseUrl,
            'timeout' => Config::get('python_api.timeout', 30),
            'headers' => [
                'Content-Type' => 'application/json',
                'Accept' => 'application/json',
            ],
        ]);
    }
    
    /**
     * Health check
     */
    public function healthCheck(): array
    {
        $response = $this->client->get('/health');
        return json_decode($response->getBody()->getContents(), true);
    }
    
    /**
     * Submit processing job
     */
    public function submitJob(array $jobData): array
    {
        $response = $this->client->post('/api/jobs', [
            'json' => $jobData,
            'headers' => [
                'Authorization' => 'Bearer ' . ($_SESSION['access_token'] ?? ''),
            ],
        ]);
        
        return json_decode($response->getBody()->getContents(), true);
    }
    
    /**
     * Get job status
     */
    public function getJobStatus(string $jobId): array
    {
        $response = $this->client->get('/api/jobs/' . $jobId . '/status');
        return json_decode($response->getBody()->getContents(), true);
    }
    
    /**
     * Get communications for a case
     */
    public function getCommunications(int $caseId, array $filters = []): array
    {
        $query = array_merge(['case_id' => $caseId], $filters);
        $response = $this->client->get('/api/results/communications?' . http_build_query($query));
        return json_decode($response->getBody()->getContents(), true);
    }
    
    /**
     * Get attachments for a case
     */
    public function getAttachments(int $caseId): array
    {
        $response = $this->client->get('/api/results/attachments?case_id=' . $caseId);
        return json_decode($response->getBody()->getContents(), true);
    }
    
    /**
     * Get timeline data
     */
    public function getTimeline(int $caseId): array
    {
        $response = $this->client->get('/api/results/timeline?case_id=' . $caseId);
        return json_decode($response->getBody()->getContents(), true);
    }
    
    /**
     * Get network visualization data
     */
    public function getNetworkData(int $caseId): array
    {
        $response = $this->client->get('/api/results/network?case_id=' . $caseId);
        return json_decode($response->getBody()->getContents(), true);
    }
    
    /**
     * Get GPS data for map
     */
    public function getGPSData(int $caseId): array
    {
        $response = $this->client->get('/api/results/gps?case_id=' . $caseId);
        return json_decode($response->getBody()->getContents(), true);
    }
}
