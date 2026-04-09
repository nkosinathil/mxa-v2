<?php

declare(strict_types=1);

require_once __DIR__ . '/../src/bootstrap.php';

if (Auth::isAuthenticated()) {
    header('Location: /');
    exit;
}

$state = bin2hex(random_bytes(16));
$_SESSION['oauth_state'] = $state;
$client = new SsoClient();

header('Location: ' . $client->authorizeUrl($state));
exit;
