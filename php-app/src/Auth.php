<?php

declare(strict_types=1);

final class Auth
{
    public static function isAuthenticated(): bool
    {
        return isset($_SESSION['user']) && is_array($_SESSION['user']);
    }

    /**
     * @return array<string, mixed>
     */
    public static function user(): array
    {
        return $_SESSION['user'] ?? [];
    }

    /**
     * @param array<string, mixed> $user
     */
    public static function login(array $user): void
    {
        $_SESSION['user'] = $user;
    }

    public static function logout(): void
    {
        $_SESSION = [];
        if (ini_get('session.use_cookies')) {
            $params = session_get_cookie_params();
            setcookie(session_name(), '', time() - 42000, $params['path'], $params['domain'], (bool) $params['secure'], (bool) $params['httponly']);
        }
        session_destroy();
    }

    public static function requireAuth(): void
    {
        if (!self::isAuthenticated()) {
            header('Location: /login.php');
            exit;
        }
    }
}
