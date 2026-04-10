<?php

declare(strict_types=1);

require_once __DIR__ . '/../src/bootstrap.php';

$state = (string) ($_GET['state'] ?? '');
$code = (string) ($_GET['code'] ?? '');
$expectedState = (string) ($_SESSION['oauth_state'] ?? '');

if ($state === '' || $expectedState === '' || !hash_equals($expectedState, $state)) {
    http_response_code(400);
    echo 'Invalid OAuth state.';
    exit;
}

if ($code === '') {
    http_response_code(400);
    echo 'Missing authorization code.';
    exit;
}

try {
    $sso = new SsoClient();
    $token = $sso->exchangeCodeForToken($code);
    $accessToken = (string) ($token['access_token'] ?? '');
    if ($accessToken === '') {
        throw new RuntimeException('No access token returned from SSO.');
    }

    $user = $sso->fetchUserInfo($accessToken);
    Auth::login($user);
    unset($_SESSION['oauth_state']);

    header('Location: /');
    exit;
} catch (Throwable $e) {
    app_log('SSO callback failed: ' . $e->getMessage());
    http_response_code(500);
    echo 'Authentication failed.';
}
