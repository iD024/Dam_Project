import os
import pytest
from importlib import reload

def test_cors_origins_defaults():
    # Clear environment variable
    if "CORS_ORIGINS" in os.environ:
        del os.environ["CORS_ORIGINS"]
    
    import backend.config as config_module
    reload(config_module)
    settings = config_module.settings
    
    assert "http://localhost:3000" in settings.CORS_ORIGINS
    assert "http://127.0.0.1:3000" in settings.CORS_ORIGINS

def test_cors_origins_from_env():
    # Set comma-separated origins from environment
    os.environ["CORS_ORIGINS"] = "https://my-dam-app.vercel.app, https://dam-project.vercel.app , http://localhost:3000"
    
    import backend.config as config_module
    reload(config_module)
    settings = config_module.settings
    
    assert "https://my-dam-app.vercel.app" in settings.CORS_ORIGINS
    assert "https://dam-project.vercel.app" in settings.CORS_ORIGINS
    assert "http://localhost:3000" in settings.CORS_ORIGINS
    # Whitespace must be cleanly stripped
    assert " https://dam-project.vercel.app " not in settings.CORS_ORIGINS
    
    # Cleanup
    del os.environ["CORS_ORIGINS"]
    reload(config_module)
