<?php

declare(strict_types=1);

function h(string $value): string
{
    return htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

function app_log(string $message): void
{
    $logDir = Env::get('LOG_DIR', __DIR__ . '/../storage/logs') ?? (__DIR__ . '/../storage/logs');
    if (!is_dir($logDir)) {
        @mkdir($logDir, 0775, true);
    }

    $line = '[' . date('c') . '] ' . $message . PHP_EOL;
    @file_put_contents($logDir . '/app.log', $line, FILE_APPEND);
}
