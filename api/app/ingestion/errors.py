class MissingProviderKeysError(RuntimeError):
    """USE_DEMO_DATA=false but a required provider API key is missing.

    Ingestion functions run inside a long-lived server process via HTTP
    cron endpoints — raise this rather than calling sys.exit(), which would
    kill the whole worker process instead of just failing one request/job.
    Only a CLI entry point should catch this and exit the process for it.
    """
