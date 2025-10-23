# rxconfig.py
import reflex as rx

config = rx.Config(
    app_name="autofix_dashboard",
    db_url="sqlite:///reflex.db",
    port=3000,  # Changed from 3001
    backend_port=8001,
    disable_plugins=['reflex.plugins.sitemap.SitemapPlugin'],
    
    # ← FIX: Allow WebSocket connections
    cors_allowed_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ],
)
