<?php

declare(strict_types=1);

final class SsoClient
{
    public function authorizeUrl(string $state): string
    {
        $query = http_build_query([
            'client_id' => Env::get('SSO_CLIENT_ID', ''),
            'redirect_uri' => Env::get('SSO_REDIRECT_URI', ''),
            'response_type' => 'code',
            'scope' => Env::get('SSO_SCOPES', 'openid profile email'),
            'state' => $state,
        ]);

        return rtrim((string) Env::get('SSO_AUTHORIZE_URL', ''), '?') . '?' . $query;
    }

    /**
     * @return array<string, mixed>
     */
    public function exchangeCodeForToken(string $code): array
    {
        $response = $this->postForm((string) Env::get('SSO_TOKEN_URL', ''), [
            'grant_type' => 'authorization_code',
            'code' => $code,
            'client_id' => Env::get('SSO_CLIENT_ID', ''),
            'client_secret' => Env::get('SSO_CLIENT_SECRET', ''),
            'redirect_uri' => Env::get('SSO_REDIRECT_URI', ''),
        ]);

        return json_decode($response, true, flags: JSON_THROW_ON_ERROR);
    }

    /**
     * @return array<string, mixed>
     */
    public function fetchUserInfo(string $accessToken): array
    {
        $ch = curl_init((string) Env::get('SSO_USERINFO_URL', ''));
        if ($ch === false) {
            throw new RuntimeException('Failed to initialize userinfo request.');
        }

        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_HTTPHEADER => [
                'Authorization: Bearer ' . $accessToken,
                'Accept: application/json',
            ],
        ]);

        $raw = curl_exec($ch);
        if ($raw === false) {
            $error = curl_error($ch);
            curl_close($ch);
            throw new RuntimeException('Userinfo request failed: ' . $error);
        }

        $httpCode = curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
        curl_close($ch);

        if ($httpCode < 200 || $httpCode >= 300) {
            throw new RuntimeException('Userinfo request returned status ' . $httpCode);
        }

        return json_decode($raw, true, flags: JSON_THROW_ON_ERROR);
    }

    /**
     * @param array<string, string|null> $data
     */
    private function postForm(string $url, array $data): string
    {
        $ch = curl_init($url);
        if ($ch === false) {
            throw new RuntimeException('Failed to initialize SSO token request.');
        }

        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_POST => true,
            CURLOPT_HTTPHEADER => ['Content-Type: application/x-www-form-urlencoded'],
            CURLOPT_POSTFIELDS => http_build_query($data),
        ]);

        $raw = curl_exec($ch);
        if ($raw === false) {
            $error = curl_error($ch);
            curl_close($ch);
            throw new RuntimeException('SSO token request failed: ' . $error);
        }

        $httpCode = curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
        curl_close($ch);

        if ($httpCode < 200 || $httpCode >= 300) {
            throw new RuntimeException('SSO token request returned status ' . $httpCode);
        }

        return $raw;
    }
}
