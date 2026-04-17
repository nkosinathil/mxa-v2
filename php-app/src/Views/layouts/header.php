<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo htmlspecialchars($config['app']['name'] ?? 'MxA Mobile'); ?></title>
    <link rel="stylesheet" href="/assets/css/main.css">
</head>
<body>
    <header class="header">
        <div class="container">
            <div class="header-content">
                <h1 class="logo">MxA Mobile</h1>
                <?php if (isset($_SESSION['user_id'])): ?>
                    <nav class="nav">
                        <a href="/dashboard">Dashboard</a>
                        <a href="/cases">Cases</a>
                        <a href="/upload">Upload</a>
                        <a href="/jobs">Jobs</a>
                        <?php if (in_array('admin', $_SESSION['user_roles'] ?? [])): ?>
                            <a href="/admin">Admin</a>
                        <?php endif; ?>
                    </nav>
                    <div class="user-menu">
                        <span><?php echo htmlspecialchars($_SESSION['user_name'] ?? 'User'); ?></span>
                        <a href="/auth/logout" class="btn btn-secondary">Logout</a>
                    </div>
                <?php endif; ?>
            </div>
        </div>
    </header>
    
    <main class="main-content">
        <div class="container">
            <?php if (isset($_SESSION['success'])): ?>
                <div class="alert alert-success">
                    <?php echo htmlspecialchars($_SESSION['success']); unset($_SESSION['success']); ?>
                </div>
            <?php endif; ?>
            
            <?php if (isset($_SESSION['error'])): ?>
                <div class="alert alert-error">
                    <?php echo htmlspecialchars($_SESSION['error']); unset($_SESSION['error']); ?>
                </div>
            <?php endif; ?>
