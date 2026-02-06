/** Configuration persisted via store.set("config", ...) */
export interface ExampleConfig {
  /** URL to fetch data from */
  serverUrl: string;
  /** API key for authentication */
  apiKey: string;
  /** Refresh interval in seconds */
  refreshInterval: number;
  /** Whether to send notifications on error */
  notifyOnError: boolean;
  /** Webhook URL for external notifications */
  webhookUrl: string;
  /** Enable verbose logging */
  verbose: boolean;
}

/** Default configuration values */
export const DEFAULT_CONFIG: ExampleConfig = {
  serverUrl: '',
  apiKey: '',
  refreshInterval: 30,
  notifyOnError: true,
  webhookUrl: '',
  verbose: false,
};
