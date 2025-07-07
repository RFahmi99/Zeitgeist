#!/usr/bin/env python3

"""
FIXED Autonomous Blog System - Main Entry Point with BULLETPROOF Session Cleanup
"""

from dotenv import load_dotenv
load_dotenv()

import asyncio
import signal
import atexit
import logging
from pathlib import Path
from flask import Flask, jsonify
import threading
import sys
import os

from src.monitoring.health_check import health_monitor
from security_enhancements import create_secure_app
from config import config
from src.monitoring.alerts import initialize_alerts

initialize_alerts(config)
app = create_secure_app()

# Add both project root and src directory to path
project_root = Path(__file__).parent
src_path = project_root / "src"

class BlogSystemManager:
    """FIXED: Main system manager with bulletproof async lifecycle management"""
    
    def __init__(self, app, config_path: str = None):
        self.app = app
        self.config = config
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # System state
        self.running = False
        self.shutdown_requested = False
        self.cleanup_completed = False
        
        # Event loop and threading
        self.main_loop = None
        self.flask_app = None
        self.flask_thread = None
        self.scheduler = None
        
        # CRITICAL: Setup proper signal handlers for async cleanup
        self._setup_signal_handlers()
        
        # Emergency cleanup registration
        atexit.register(self._emergency_sync_cleanup)
    
    def _setup_signal_handlers(self):
        """Setup async-aware signal handlers"""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, requesting shutdown...")
            self.shutdown_requested = True
            
            # CRITICAL: Handle async cleanup properly
            if self.main_loop and self.main_loop.is_running():
                # Schedule cleanup in the event loop
                asyncio.run_coroutine_threadsafe(self.async_shutdown(), self.main_loop)
            else:
                # Fallback to sync cleanup
                self._emergency_sync_cleanup()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _emergency_sync_cleanup(self):
        """Emergency synchronous cleanup for atexit"""
        if self.cleanup_completed:
            return
            
        self.logger.warning("Emergency synchronous cleanup triggered!")
        try:
            # Import here to avoid circular imports
            from src.aggregator.article_fetcher import browser_manager
            
            # Cleanup browser (synchronous)
            browser_manager.cleanup()
            
            # For async resources, we need to create a new event loop
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Import async components
                from src.aggregator.article_fetcher import async_fetcher, emergency_cleanup
                
                # Run emergency cleanup
                loop.run_until_complete(emergency_cleanup())
                loop.close()
                
                self.logger.info("Emergency cleanup completed")
            except Exception as e:
                self.logger.error(f"Emergency async cleanup failed: {e}")
                
        except Exception as e:
            self.logger.error(f"Emergency cleanup failed: {e}")
        finally:
            self.cleanup_completed = True
    
    def setup_web_interface(self):
        """Setup Flask web interface with health endpoint"""
        self.flask_app = self.app
        
        @self.flask_app.route('/health', methods=['GET'])
        def web_health_check():
            health_status = health_monitor.perform_health_check()
            http_status = 200
            if health_status.status == 'degraded':
                http_status = 200  # Still okay for load balancers
            elif health_status.status == 'unhealthy':
                http_status = 503  # Service unavailable
            
            return jsonify({
                'status': health_status.status,
                'timestamp': health_status.timestamp,
                'checks': health_status.checks,
                'response_time_ms': health_status.response_time_ms
            }), http_status
        
        @self.flask_app.route('/status', methods=['GET'])
        def system_status():
            return jsonify({
                'system': 'Autonomous Blog System',
                'version': '2.0',
                'config': self.config.get_summary(),
                'uptime': health_monitor.get_uptime()
            })
        
        @self.flask_app.route('/shutdown', methods=['POST'])
        def trigger_shutdown():
            """Endpoint to trigger graceful shutdown"""
            self.shutdown_requested = True
            if self.main_loop and self.main_loop.is_running():
                asyncio.run_coroutine_threadsafe(self.async_shutdown(), self.main_loop)
            return jsonify({'status': 'shutdown_requested'}), 200
    
    def start_web_interface(self):
        """Start Flask web interface in separate thread"""
        if self.app:
            self.flask_thread = threading.Thread(
                target=lambda: self.flask_app.run(
                    host='0.0.0.0',
                    port=8000,
                    debug=False,
                    use_reloader=False
                )
            )
            self.flask_thread.daemon = True
            self.flask_thread.start()
            self.logger.info("Web interface started on port 8000")
    
    def _setup_logging(self):
        """Setup logging with rotation for entire system"""
        from logging.handlers import RotatingFileHandler
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.config.logging.level))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # File handler with rotation
        file_handler = RotatingFileHandler(
            self.config.logging.file,
            maxBytes=self.config.logging.max_size_mb * 1024 * 1024,
            backupCount=self.config.logging.backup_count
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        return logging.getLogger('blog_system.manager')
    
    def startup(self, run_once=False):
        """Start all system components"""
        self.logger.info("Starting blog system...")
        
        # Validate configuration
        validation_issues = self.config.validate()
        if validation_issues:
            self.logger.warning(f"Configuration issues: {validation_issues}")
        
        # Log configuration summary
        self.logger.info(f"Configuration: {self.config.get_summary()}")
        
        self.setup_web_interface()
        self.start_web_interface()
        
        # Only start scheduler for continuous operation
        if self.config.scheduling.enabled and not run_once:
            from src.scheduler.schedule import blog_scheduler
            self.scheduler = blog_scheduler
            self.scheduler.start_scheduling()
        
        self.running = True
        self.logger.info("Blog system started successfully")
    
    async def async_shutdown(self):
        """FIXED: Async shutdown with bulletproof session cleanup and proper timing"""
        if self.cleanup_completed:
            return
            
        self.logger.info("Starting async shutdown...")
        self.shutdown_requested = True
        
        try:
            # STEP 1: Stop scheduler gracefully
            if self.scheduler:
                self.logger.info("Stopping scheduler...")
                await self.scheduler.shutdown()
                self.logger.info("Scheduler stopped")
            
            # STEP 2: Wait for any ongoing operations
            self.logger.info("Waiting for ongoing operations to complete...")
            await asyncio.sleep(3.0)  # Give time for current operations
            
            # STEP 3: Import and cleanup async components
            try:
                from src.aggregator.article_fetcher import async_fetcher
                
                # STEP 4: Clean up async fetcher
                self.logger.info("Cleaning up async fetcher...")
                await async_fetcher.cleanup()
                
                self.logger.info("Async components cleaned up successfully")
            except ImportError as e:
                self.logger.warning(f"Could not import async components: {e}")
            except Exception as e:
                self.logger.error(f"Error during async cleanup: {e}")
            
            # STEP 5: Cleanup browser resources (sync)
            try:
                from src.aggregator.article_fetcher import browser_manager
                browser_manager.cleanup()
                self.logger.info("Browser resources cleaned up")
            except Exception as e:
                self.logger.error(f"Error during browser cleanup: {e}")
            
            # STEP 6: CRITICAL - Extended wait for all cleanup to complete
            self.logger.info("Waiting for final cleanup...")
            await asyncio.sleep(2.0)  # Increased wait time
            
            # STEP 7: Force garbage collection
            import gc
            gc.collect()
            
            self.running = False
            self.cleanup_completed = True
            self.logger.info("Async shutdown completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error during async shutdown: {e}")
            self.cleanup_completed = True
    
    async def run_single_cycle(self):
        """FIXED: Run single cycle with comprehensive cleanup"""
        self.logger.info("Running single blog generation cycle...")
        
        try:
            from src.scheduler.schedule import blog_scheduler
            await blog_scheduler.blog_generation_task()
            
        except Exception as e:
            self.logger.error(f"Blog generation task failed: {e}")
            raise
        finally:
            # CRITICAL: Always cleanup after single cycle with extended timing
            self.logger.info("Cleaning up after single cycle...")
            try:
                from src.aggregator.article_fetcher import async_fetcher
                await async_fetcher.cleanup()
                
                # Extra wait for cleanup
                await asyncio.sleep(2.0)  # Increased wait time
                
                # Force garbage collection
                import gc
                gc.collect()
                
                self.logger.info("Single cycle cleanup completed")
                
            except Exception as e:
                self.logger.error(f"Single cycle cleanup failed: {e}")

async def async_main():
    """FIXED: Async main with proper event loop management and extended cleanup"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Autonomous Blog System')
    parser.add_argument('--run-once', action='store_true', help='Run single cycle and exit')
    args = parser.parse_args()
    
    system = BlogSystemManager(app=app)
    
    # CRITICAL: Store the event loop reference
    system.main_loop = asyncio.get_running_loop()
    
    try:
        system.startup(run_once=args.run_once)
        
        if args.run_once:
            await system.run_single_cycle()
        else:
            # Keep running until shutdown
            while system.running and not system.shutdown_requested:
                await asyncio.sleep(1)
                
    except KeyboardInterrupt:
        print("\nShutdown requested via keyboard interrupt...")
        system.shutdown_requested = True
    except Exception as e:
        system.logger.error(f"Fatal error: {str(e)}")
        raise
    finally:
        # CRITICAL: Always run async cleanup with extended wait
        if not system.cleanup_completed:
            print("Performing final cleanup...")
            await system.async_shutdown()
            
            # FINAL WAIT: Ensure all async operations are truly complete
            print("Final wait for async operations...")
            await asyncio.sleep(3.0)
            
            print("Cleanup completed")

def main():
    """FIXED: Main entry point with proper async lifecycle and error handling"""
    try:
        # CRITICAL: Use asyncio.run() for proper lifecycle management
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\nApplication terminated by user")
    except Exception as e:
        print(f"Application failed: {e}")
        sys.exit(1)
    finally:
        print("Application shutdown complete")

if __name__ == "__main__":
    main()