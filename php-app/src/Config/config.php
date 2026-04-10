<?php
/**
 * Application Configuration
 * 
 * Loads environment variables and sets up application configuration.
 */

declare(strict_types=1);

namespace App\Config;

class Config
{
    private static array $config = [];
    
    public static function load(): void
    {
        self::$config = [
            'app' => [
                'name' => $_ENV['PRODUCT_NAME'] ?? 'MxA Mobile',
                'env' => $_ENV['APP_ENV'] ?? 'production',
                'debug' => filter_var($_ENV['APP_DEBUG'] ?? 'false', FILTER_VALIDATE_BOOLEAN),
                'url' => $_ENV['APP_URL'] ?? 'http://192.168.1.66',
                'key' => $_ENV['APP_KEY'] ?? '',
            ],
            'database' => [
                'host' => $_ENV['DB_HOST'] ?? '192.168.1.66',
                'port' => (int)($_ENV['DB_PORT'] ?? 5432),
                'database' => $_ENV['DB_NAME'] ?? 'mxa_mobile',
                'username' => $_ENV['DB_USER'] ?? 'mxa_mobile_user',
                'password' => $_ENV['DB_PASSWORD'] ?? '',
                'charset' => 'utf8',
            ],
            'keycloak' => [
                'server_url' => $_ENV['KEYCLOAK_SERVER_URL'] ?? '',
                'realm' => $_ENV['KEYCLOAK_REALM'] ?? 'forensics',
                'client_id' => $_ENV['KEYCLOAK_CLIENT_ID'] ?? 'mxa-mobile-web',
                'client_secret' => $_ENV['KEYCLOAK_CLIENT_SECRET'] ?? '',
                'redirect_uri' => $_ENV['KEYCLOAK_REDIRECT_URI'] ?? '',
            ],
            'python_api' => [
                'url' => $_ENV['PYTHON_API_URL'] ?? 'http://192.168.1.90:8104',
                'timeout' => 30,
            ],
            'minio' => [
                'endpoint' => $_ENV['MINIO_ENDPOINT'] ?? '192.168.1.90:9000',
                'access_key' => $_ENV['MINIO_ACCESS_KEY'] ?? '',
                'secret_key' => $_ENV['MINIO_SECRET_KEY'] ?? '',
                'use_ssl' => filter_var($_ENV['MINIO_USE_SSL'] ?? 'false', FILTER_VALIDATE_BOOLEAN),
                'region' => $_ENV['MINIO_REGION'] ?? 'us-east-1',
                'bucket_input' => $_ENV['MINIO_BUCKET_INPUT'] ?? 'mxa-mobile-input',
                'bucket_output' => $_ENV['MINIO_BUCKET_OUTPUT'] ?? 'mxa-mobile-output',
            ],
            'session' => [
                'lifetime' => (int)($_ENV['SESSION_LIFETIME'] ?? 7200),
                'secure' => filter_var($_ENV['SESSION_SECURE'] ?? 'false', FILTER_VALIDATE_BOOLEAN),
                'http_only' => true,
                'same_site' => 'Lax',
            ],
            'logging' => [
                'level' => $_ENV['LOG_LEVEL'] ?? 'info',
                'path' => $_ENV['LOG_PATH'] ?? STORAGE_PATH . '/logs',
            ],
        ];
    }
    
    public static function get(string $key, $default = null)
    {
        if (empty(self::$config)) {
            self::load();
        }
        
        $keys = explode('.', $key);
        $value = self::$config;
        
        foreach ($keys as $k) {
            if (!isset($value[$k])) {
                return $default;
            }
            $value = $value[$k];
        }
        
        return $value;
    }
    
    public static function all(): array
    {
        if (empty(self::$config)) {
            self::load();
        }
        return self::$config;
    }
}

// Load configuration
Config::load();
