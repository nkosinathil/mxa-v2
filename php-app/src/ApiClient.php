<?php

declare(strict_types=1);

final class ApiClient
{
    private string $baseUrl;
    private string $apiKey;

    public function __construct()
    {
        $this->baseUrl = rtrim((string) Env::get('PYTHON_API_BASE_URL', ''), '/');
        $this->apiKey = (string) Env::get('PYTHON_API_KEY', '');
    }

    /**
     * @param array<string, mixed> $payload
     * @return array<string, mixed>
     */
    public function submitJob(array $payload, string $filePath, string $originalName): array
    {
        if (!is_file($filePath)) {
            throw new RuntimeException('Upload file not found for API transfer.');
        }

        $cFile = curl_file_create($filePath, mime_content_type($filePath) ?: 'application/octet-stream', $originalName);
        $fields = [
            'payload' => json_encode($payload, JSON_THROW_ON_ERROR),
            'evidence' => $cFile,
        ];

        return $this->requestMultipart('POST', '/v1/jobs', $fields);
    }

    /**
     * @return array<string, mixed>
     */
    public function getJob(string $jobId): array
    {
        return $this->requestJson('GET', '/v1/jobs/' . rawurlencode($jobId));
    }

    /**
     * @return array<string, mixed>
     */
    public function health(): array
    {
        return $this->requestJson('GET', '/health');
    }

    /**
     * @param array<string, mixed> $fields
     * @return array<string, mixed>
     */
    private function requestMultipart(string $method, string $path, array $fields): array
    {
        $ch = curl_init($this->baseUrl . $path);
        if ($ch === false) {
            throw new RuntimeException('Failed to initialize API request.');
        }

        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_CUSTOMREQUEST => $method,
            CURLOPT_POSTFIELDS => $fields,
            CURLOPT_HTTPHEADER => $this->headers(),
        ]);

        return $this->decodeResponse($ch);
    }

    /**
     * @return array<string, mixed>
     */
    private function requestJson(string $method, string $path): array
    {
        $ch = curl_init($this->baseUrl . $path);
        if ($ch === false) {
            throw new RuntimeException('Failed to initialize API request.');
        }

        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_CUSTOMREQUEST => $method,
            CURLOPT_HTTPHEADER => array_merge($this->headers(), ['Accept: application/json']),
        ]);

        return $this->decodeResponse($ch);
    }

    /**
     * @return list<string>
     */
    private function headers(): array
    {
        $headers = ['X-API-Key: ' . $this->apiKey];
        return $headers;
    }

    /**
     * @return array<string, mixed>
     */
    private function decodeResponse($ch): array
    {
        $raw = curl_exec($ch);
        if ($raw === false) {
            $error = curl_error($ch);
            curl_close($ch);
            throw new RuntimeException('API request failed: ' . $error);
        }

        $httpCode = curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
        curl_close($ch);

        $data = json_decode($raw, true);
        if (!is_array($data)) {
            throw new RuntimeException('Invalid API response payload.');
        }

        if ($httpCode < 200 || $httpCode >= 300) {
            $message = is_string($data['detail'] ?? null) ? $data['detail'] : ('API request failed with status ' . $httpCode);
            throw new RuntimeException($message);
        }

        return $data;
    }
}
