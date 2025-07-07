# Enhanced Security Configuration for Flask Application
import os
import secrets
from datetime import timedelta
from flask import Flask, request, g
from flask_wtf.csrf import CSRFProtect
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
import jwt
import logging
from typing import Optional, Dict, Any
import hashlib
import time

logger = logging.getLogger(__name__)

class SecurityConfig:
    """Enhanced security configuration for production Flask app"""
    
    # Generate secure secret key if not provided
    SECRET_KEY = os.getenv('SECRET_KEY') or secrets.token_urlsafe(32)
    
    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
    
    # Session Security
    SESSION_COOKIE_SECURE = True  # HTTPS only
    SESSION_COOKIE_HTTPONLY = True  # No JS access
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    
    # Content Security Policy
    CSP = {
        'default-src': "'self'",
        'script-src': ["'self'", "'nonce-{nonce}'", "https://cdn.jsdelivr.net"],
        'style-src': "'self' 'unsafe-inline' https://fonts.googleapis.com",
        'font-src': "'self' https://fonts.gstatic.com",
        'img-src': "'self' data: https:",
        'connect-src': "'self'",
    }
    
    # Force HTTPS
    FORCE_HTTPS = True
    
    # Rate limiting
    RATELIMIT_STORAGE_URL = "memory://"
    RATELIMIT_DEFAULT = "100 per hour"

class SecurityManager:
    """Comprehensive security manager for the Flask application"""
    
    def __init__(self, app: Flask = None):
        self.app = app
        self.csrf = None
        self.limiter = None
        self.failed_attempts = {}  # Track failed login attempts
        
        if app is not None:
            self.init_app(app)
            
    def init_app(self, app: Flask):
        """Initialize security extensions"""
        self.app = app
        
        # Apply security configuration
        app.config.from_object(SecurityConfig)
        
        # Initialize CSRF protection
        self.csrf = CSRFProtect(app)
        
        # Initialize rate limiting
        self.limiter = Limiter(
            key_func=get_remote_address,
            app=app,
            default_limits=["1000 per hour", "100 per minute"]
        )
        
        # Initialize Talisman for security headers
        Talisman(
            app,
            force_https=SecurityConfig.FORCE_HTTPS,
            content_security_policy=SecurityConfig.CSP,
            content_security_policy_nonce_in=['script-src'],
            feature_policy={
                'geolocation': "'none'",
                'camera': "'none'",
                'microphone': "'none'",
            },
            permissions_policy={
                'geolocation': '()',
                'camera': '()',
                'microphone': '()',
            }
        )
        
        # Register security middleware
        self._register_security_middleware()
        
    def _register_security_middleware(self):
        """Register security middleware functions"""
        
        @self.app.before_request
        def security_headers():
            """Add additional security headers"""
            # Add custom security headers
            g.request_start_time = time.time()
            g.request_id = secrets.token_urlsafe(8)
            
            # Log security-relevant requests
            if request.endpoint in ['admin', 'api', 'upload']:
                logger.info(f"Security-relevant request: {request.endpoint} from {request.remote_addr}")
                
        @self.app.after_request
        def after_request(response):
            """Add security headers to response"""
            response.headers['X-Request-ID'] = g.get('request_id', 'unknown')
            response.headers['X-Response-Time'] = f"{(time.time() - g.get('request_start_time', time.time())) * 1000:.2f}ms"
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            response.headers['X-Permitted-Cross-Domain-Policies'] = 'none'
            
            return response
        
        @self.app.after_request
        def add_csp_nonce(response):
            nonce = secrets.token_hex(16)
            response.headers['Content-Security-Policy'] = SecurityConfig.CSP.replace('{nonce}', nonce)
            return response

            
    def create_api_key(self, identifier: str, permissions: list = None) -> str:
        """Create a secure API key for authentication"""
        payload = {
            'identifier': identifier,
            'permissions': permissions or ['read'],
            'created_at': time.time(),
            'expires_at': time.time() + (30 * 24 * 60 * 60)  # 30 days
        }
        
        return jwt.encode(payload, self.app.config['SECRET_KEY'], algorithm='HS256')
        
    def verify_api_key(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode an API key"""
        try:
            payload = jwt.decode(token, self.app.config['SECRET_KEY'], algorithms=['HS256'])
            
            # Check expiration
            if payload.get('expires_at', 0) < time.time():
                return None
                
            return payload
        except jwt.InvalidTokenError:
            return None
            
    def require_api_key(self, required_permissions: list = None):
        """Decorator to require API key authentication"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # Get API key from header or query parameter
                api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
                
                if not api_key:
                    return {'error': 'API key required'}, 401
                    
                payload = self.verify_api_key(api_key)
                if not payload:
                    return {'error': 'Invalid API key'}, 401
                    
                # Check permissions
                if required_permissions:
                    user_permissions = payload.get('permissions', [])
                    if not any(perm in user_permissions for perm in required_permissions):
                        return {'error': 'Insufficient permissions'}, 403
                        
                g.api_user = payload
                return f(*args, **kwargs)
            return decorated_function
        return decorator
        
    def track_failed_attempt(self, identifier: str):
        """Track failed login attempts for rate limiting"""
        current_time = time.time()
        
        if identifier not in self.failed_attempts:
            self.failed_attempts[identifier] = []
            
        # Clean old attempts (older than 1 hour)
        cutoff_time = current_time - 3600
        self.failed_attempts[identifier] = [
            attempt_time for attempt_time in self.failed_attempts[identifier]
            if attempt_time > cutoff_time
        ]
        
        self.failed_attempts[identifier].append(current_time)
        
    def is_blocked(self, identifier: str, max_attempts: int = 5) -> bool:
        """Check if an identifier is blocked due to too many failed attempts"""
        if identifier not in self.failed_attempts:
            return False
            
        return len(self.failed_attempts[identifier]) >= max_attempts
        
    def clear_failed_attempts(self, identifier: str):
        """Clear failed attempts for successful login"""
        if identifier in self.failed_attempts:
            del self.failed_attempts[identifier]

class InputValidator:
    """Input validation and sanitization utilities"""
    
    @staticmethod
    def sanitize_html(text: str) -> str:
        """Sanitize HTML input to prevent XSS"""
        try:
            import bleach
            allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li', 'h1', 'h2', 'h3']
            allowed_attributes = {}
            
            return bleach.clean(text, tags=allowed_tags, attributes=allowed_attributes, strip=True)
        except ImportError:
            # Fallback: basic HTML escaping
            import html
            return html.escape(text)
            
    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format and safety"""
        try:
            from urllib.parse import urlparse
            result = urlparse(url)
            
            # Check for valid scheme and netloc
            if not result.scheme or not result.netloc:
                return False
                
            # Block dangerous schemes
            if result.scheme not in ['http', 'https']:
                return False
                
            # Block localhost and internal IPs in production
            if os.getenv('FLASK_ENV') == 'production':
                import ipaddress
                try:
                    ip = ipaddress.ip_address(result.netloc.split(':')[0])
                    if ip.is_private or ip.is_loopback:
                        return False
                except ValueError:
                    pass  # Not an IP address, continue validation
                    
            return True
        except Exception:
            return False
            
    @staticmethod
    def validate_file_upload(file, allowed_extensions: set, max_size_mb: int = 10):
        """Validate file uploads for security"""
        if not file or not file.filename:
            return False, "No file provided"
            
        # Check file extension
        if '.' not in file.filename:
            return False, "File must have an extension"
            
        extension = file.filename.rsplit('.', 1)[1].lower()
        if extension not in allowed_extensions:
            return False, f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"
            
        # Check file size
        file.seek(0, 2)  # Seek to end
        size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if size > max_size_mb * 1024 * 1024:
            return False, f"File too large. Maximum size: {max_size_mb}MB"
            
        # Check for executable files (basic security)
        dangerous_extensions = {'exe', 'bat', 'cmd', 'com', 'pif', 'scr', 'vbs', 'js'}
        if extension in dangerous_extensions:
            return False, "Executable files not allowed"
            
        return True, "File is valid"

# Enhanced Flask App Factory with Security
def create_secure_app(config_name: str = 'production') -> Flask:
    """Create a Flask app with comprehensive security measures"""
    
    app = Flask(__name__)
    
    # Initialize security manager
    security_manager = SecurityManager(app)

    logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(logs_dir, exist_ok=True)

    # Configure logging with security context
    if not app.debug:
        import logging
        from logging.handlers import RotatingFileHandler
        
        # Security log handler
        security_handler = RotatingFileHandler(
            'logs/security.log', maxBytes=10240000, backupCount=10
        )
        security_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d] [%(request_id)s]'
        ))
        security_handler.setLevel(logging.WARNING)
        app.logger.addHandler(security_handler)
        
    # Register security routes
    @app.route('/api/health')
    @security_manager.limiter.limit("10 per minute")
    def health_check():
        """Health check endpoint with rate limiting"""
        return {
            'status': 'healthy',
            'timestamp': time.time(),
            'version': '2.0'
        }
        
    @app.route('/api/admin/metrics')
    @security_manager.require_api_key(['admin', 'read'])
    def admin_metrics():
        """Admin metrics endpoint with API key protection"""
        return {
            'metrics': 'placeholder',
            'user': g.api_user['identifier']
        }
        
    # Error handlers with security logging
    @app.errorhandler(429)
    def rate_limit_handler(e):
        logger.warning(f"Rate limit exceeded from {request.remote_addr}")
        return {'error': 'Rate limit exceeded'}, 429
        
    @app.errorhandler(403)
    def forbidden_handler(e):
        logger.warning(f"Forbidden access attempt from {request.remote_addr} to {request.endpoint}")
        return {'error': 'Access forbidden'}, 403
        
    return app

# Security utilities
class SecurityUtils:
    """Security utility functions"""
    
    @staticmethod
    def generate_secure_filename(filename: str) -> str:
        """Generate a secure filename to prevent directory traversal"""
        import os
        import unicodedata
        import re
        
        # Remove path components
        filename = os.path.basename(filename)
        
        # Normalize unicode characters
        filename = unicodedata.normalize('NFKD', filename)
        
        # Remove dangerous characters
        filename = re.sub(r'[^\w\s.-]', '', filename).strip()
        
        # Limit length
        if len(filename) > 100:
            name, ext = os.path.splitext(filename)
            filename = name[:95] + ext
            
        # Add timestamp prefix to ensure uniqueness
        timestamp = str(int(time.time()))
        return f"{timestamp}_{filename}"
        
    @staticmethod
    def hash_sensitive_data(data: str, salt: str = None) -> str:
        """Hash sensitive data with salt"""
        if salt is None:
            salt = secrets.token_hex(16)
            
        hashed = hashlib.pbkdf2_hmac('sha256', data.encode(), salt.encode(), 100000)
        return f"{salt}:{hashed.hex()}"
        
    @staticmethod
    def verify_hashed_data(data: str, hashed: str) -> bool:
        """Verify hashed data"""
        try:
            salt, stored_hash = hashed.split(':', 1)
            new_hash = hashlib.pbkdf2_hmac('sha256', data.encode(), salt.encode(), 100000)
            return stored_hash == new_hash.hex()
        except ValueError:
            return False

# Usage example and integration guide
"""
To integrate this security system into your existing Flask app:

1. Update main.py:
   from security_enhancements import create_secure_app, SecurityManager
   
   app = create_secure_app()

2. Add to requirements.txt:
   flask-wtf
   flask-talisman
   flask-limiter
   pyjwt
   bleach

3. Set environment variables:
   SECRET_KEY=your-super-secret-key-here
   FLASK_ENV=production

4. Use decorators on sensitive endpoints:
   @security_manager.require_api_key(['admin'])
   @security_manager.limiter.limit("5 per minute")
   
5. Validate all user inputs:
   from security_enhancements import InputValidator
   clean_content = InputValidator.sanitize_html(user_input)
"""