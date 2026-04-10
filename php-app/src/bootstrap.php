<?php

declare(strict_types=1);

require_once __DIR__ . '/Env.php';
Env::load(__DIR__ . '/../.env');

require_once __DIR__ . '/helpers.php';
require_once __DIR__ . '/Auth.php';
require_once __DIR__ . '/SsoClient.php';
require_once __DIR__ . '/ApiClient.php';

if (session_status() !== PHP_SESSION_ACTIVE) {
    session_name('mxa_mobile_analytics');
    session_start();
}

// Validate foundational environment configuration.
$required = [
    'PYTHON_API_BASE_URL',
    'SSO_AUTHORIZE_URL',
    'SSO_TOKEN_URL',
    'SSO_USERINFO_URL',
    'SSO_CLIENT_ID',
    'SSO_CLIENT_SECRET',
    'SSO_REDIRECT_URI',
];

foreach ($required as $var) {
    if (Env::get($var) === null || Env::get($var) === '') {
        app_log("Missing environment variable: {$var}");
    }
}
