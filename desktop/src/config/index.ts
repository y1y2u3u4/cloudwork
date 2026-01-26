/**
 * CloudWork Desktop Configuration
 *
 * Centralized configuration for the desktop application.
 * Connects to CloudWork Python API bridge.
 */

// =============================================================================
// API Configuration
// =============================================================================

/**
 * API port configuration
 * - Development: 2026 (run `python desktop/api/main.py`)
 * - Production: 2026 (CloudWork API service)
 */
export const API_PORT = import.meta.env.PROD ? 2026 : 2026;

/**
 * API base URL - connects to CloudWork Python FastAPI
 */
export const API_BASE_URL = `http://localhost:${API_PORT}`;

// =============================================================================
// App Configuration
// =============================================================================

/**
 * App name
 */
export const APP_NAME = 'CloudWork';

/**
 * App identifier (must match tauri.conf.json)
 */
export const APP_IDENTIFIER = 'com.cloudwork.desktop';
