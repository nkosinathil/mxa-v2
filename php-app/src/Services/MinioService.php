<?php
/**
 * MinIO Service
 * 
 * Handles object storage operations with MinIO (S3-compatible).
 */

declare(strict_types=1);

namespace App\Services;

use App\Config\Config;
use Aws\S3\S3Client;
use Aws\Exception\AwsException;

class MinioService
{
    private S3Client $client;
    private array $config;
    
    public function __construct()
    {
        $this->config = Config::get('minio');
        
        $this->client = new S3Client([
            'version' => 'latest',
            'region' => $this->config['region'],
            'endpoint' => ($this->config['use_ssl'] ? 'https://' : 'http://') . $this->config['endpoint'],
            'use_path_style_endpoint' => true,
            'credentials' => [
                'key' => $this->config['access_key'],
                'secret' => $this->config['secret_key'],
            ],
        ]);
    }
    
    /**
     * Upload file to MinIO
     */
    public function uploadFile(string $filePath, string $objectName, string $bucketType = 'input'): array
    {
        $bucket = $this->getBucketName($bucketType);
        
        try {
            $result = $this->client->putObject([
                'Bucket' => $bucket,
                'Key' => $objectName,
                'SourceFile' => $filePath,
            ]);
            
            return [
                'success' => true,
                'bucket' => $bucket,
                'object_name' => $objectName,
                'etag' => $result['ETag'],
            ];
        } catch (AwsException $e) {
            error_log('MinIO upload failed: ' . $e->getMessage());
            throw new \Exception('File upload failed');
        }
    }
    
    /**
     * Download file from MinIO
     */
    public function downloadFile(string $objectName, string $destinationPath, string $bucketType = 'output'): bool
    {
        $bucket = $this->getBucketName($bucketType);
        
        try {
            $this->client->getObject([
                'Bucket' => $bucket,
                'Key' => $objectName,
                'SaveAs' => $destinationPath,
            ]);
            
            return true;
        } catch (AwsException $e) {
            error_log('MinIO download failed: ' . $e->getMessage());
            return false;
        }
    }
    
    /**
     * Get presigned URL for file download
     */
    public function getPresignedUrl(string $objectName, string $bucketType = 'output', int $expiresIn = 3600): string
    {
        $bucket = $this->getBucketName($bucketType);
        
        $cmd = $this->client->getCommand('GetObject', [
            'Bucket' => $bucket,
            'Key' => $objectName,
        ]);
        
        $request = $this->client->createPresignedRequest($cmd, "+{$expiresIn} seconds");
        
        return (string)$request->getUri();
    }
    
    /**
     * List objects in bucket
     */
    public function listObjects(string $prefix = '', string $bucketType = 'output'): array
    {
        $bucket = $this->getBucketName($bucketType);
        
        try {
            $result = $this->client->listObjects([
                'Bucket' => $bucket,
                'Prefix' => $prefix,
            ]);
            
            $objects = [];
            if (isset($result['Contents'])) {
                foreach ($result['Contents'] as $object) {
                    $objects[] = [
                        'key' => $object['Key'],
                        'size' => $object['Size'],
                        'last_modified' => $object['LastModified']->format('Y-m-d H:i:s'),
                    ];
                }
            }
            
            return $objects;
        } catch (AwsException $e) {
            error_log('MinIO list failed: ' . $e->getMessage());
            return [];
        }
    }
    
    /**
     * Delete object from bucket
     */
    public function deleteObject(string $objectName, string $bucketType = 'input'): bool
    {
        $bucket = $this->getBucketName($bucketType);
        
        try {
            $this->client->deleteObject([
                'Bucket' => $bucket,
                'Key' => $objectName,
            ]);
            
            return true;
        } catch (AwsException $e) {
            error_log('MinIO delete failed: ' . $e->getMessage());
            return false;
        }
    }
    
    /**
     * Get bucket name based on type
     */
    private function getBucketName(string $type): string
    {
        $bucketMap = [
            'input' => $this->config['bucket_input'],
            'output' => $this->config['bucket_output'],
        ];
        
        return $bucketMap[$type] ?? $this->config['bucket_input'];
    }
}
