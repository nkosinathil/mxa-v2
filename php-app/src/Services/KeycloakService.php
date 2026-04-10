<?php
/**
 * Keycloak OIDC Service
 * 
 * Handles OAuth 2.0 / OIDC authentication with Keycloak.
 */

declare(strict_types=1);

namespace App\Services;

use App\Config\Config;
use GuzzleHttp\Client;

class KeycloakService
{
    private Client $client;
    private array $config;
    private ?string $state = null;
    
    public function __construct()
    {
        $this->client = new Client();
        $this->config = Config::get('keycloak');
    }
    
    /**
     * Generate OAuth authorization URL
     */
    public function getAuthorizationUrl(): string
    {
        $this->state = bin2hex(random_bytes(16));
        
        $params = [
            'client_id' => $this->config['client_id'],
            'redirect_uri' => $this->config['redirect_uri'],
            'response_type' => 'code',
            'scope' => 'openid profile email',
            'state' => $this->state,
        ];
        
        $baseUrl = sprintf(
            '%s/realms/%s/protocol/openid-connect/auth',
            $this->config['server_url'],
            $this->config['realm']
        );
        
        return $baseUrl . '?' . http_build_query($params);
    }
    
    /**
     * Exchange authorization code for access token
     */
    public function getAccessToken(string $code): array
    {
        $tokenUrl = sprintf(
            '%s/realms/%s/protocol/openid-connect/token',
            $this->config['server_url'],
            $this->config['realm']
        );
        
        $response = $this->client->post($tokenUrl, [
            'form_params' => [
                'grant_type' => 'authorization_code',
                'code' => $code,
                'client_id' => $this->config['client_id'],
                'client_secret' => $this->config['client_secret'],
                'redirect_uri' => $this->config['redirect_uri'],
            ],
        ]);
        
        return json_decode($response->getBody()->getContents(), true);
    }
    
    /**
     * Get user information from access token
     */
    public function getUserInfo(string $accessToken): array
    {
        $userInfoUrl = sprintf(
            '%s/realms/%s/protocol/openid-connect/userinfo',
            $this->config['server_url'],
            $this->config['realm']
        );
        
        $response = $this->client->get($userInfoUrl, [
            'headers' => [
                'Authorization' => 'Bearer ' . $accessToken,
            ],
        ]);
        
        return json_decode($response->getBody()->getContents(), true);
    }
    
    /**
     * Get logout URL
     */
    public function getLogoutUrl(): string
    {
        $logoutUrl = sprintf(
            '%s/realms/%s/protocol/openid-connect/logout',
            $this->config['server_url'],
            $this->config['realm']
        );
        
        $params = [
            'client_id' => $this->config['client_id'],
            'post_logout_redirect_uri' => Config::get('app.url'),
        ];
        
        return $logoutUrl . '?' . http_build_query($params);
    }
    
    /**
     * Get OAuth state value
     */
    public function getState(): ?string
    {
        return $this->state;
    }
    
    /**
     * Validate access token
     */
    public function validateToken(string $accessToken): bool
    {
        try {
            $this->getUserInfo($accessToken);
            return true;
        } catch (\Exception $e) {
            return false;
        }
    }
}
