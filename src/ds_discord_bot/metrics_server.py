"""Flask server for exposing Prometheus metrics."""

import logging
import threading

from flask import Flask, Response

from ds_common.metrics.service import get_metrics_service

logger = logging.getLogger(__name__)


class MetricsServer:
    """Flask-based HTTP server for exposing Prometheus metrics."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        """
        Initialize metrics server.

        Args:
            host: Host to bind to (default: 0.0.0.0)
            port: Port to bind to (default: 8000)
        """
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        self._server_thread: threading.Thread | None = None
        self._running = False

        # Setup routes
        @self.app.route("/metrics")
        def metrics() -> Response:
            """Expose Prometheus metrics."""
            try:
                metrics_service = get_metrics_service()
                metrics_data = metrics_service.generate_metrics()
                return Response(
                    metrics_data,
                    mimetype="text/plain; version=0.0.4; charset=utf-8",
                )
            except Exception as e:
                logger.error(f"Error generating metrics: {e}", exc_info=True)
                return Response("Error generating metrics", status=500)

        @self.app.route("/health")
        def health() -> Response:
            """Health check endpoint."""
            return Response("OK", status=200)

    def start(self) -> None:
        """Start the metrics server in a background thread."""
        if self._running:
            logger.warning("Metrics server is already running")
            return

        def run_server() -> None:
            """Run Flask server in thread."""
            try:
                logger.info(f"Starting metrics server on {self.host}:{self.port}")
                self.app.run(
                    host=self.host,
                    port=self.port,
                    debug=False,
                    use_reloader=False,
                    threaded=True,
                )
            except Exception as e:
                logger.error(f"Error running metrics server: {e}", exc_info=True)
            finally:
                self._running = False

        self._running = True
        self._server_thread = threading.Thread(target=run_server, daemon=True)
        self._server_thread.start()
        logger.info(f"Metrics server thread started (will bind to {self.host}:{self.port})")

    def stop(self) -> None:
        """Stop the metrics server."""
        if not self._running:
            return

        logger.info("Stopping metrics server...")
        # Flask's development server doesn't have a clean shutdown
        # In production, use a proper WSGI server like gunicorn
        # For now, we'll just mark it as stopped
        self._running = False
        logger.info("Metrics server stopped")

    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running
