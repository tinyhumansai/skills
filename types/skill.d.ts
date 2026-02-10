interface Skill {
  info: {
    id: string;
    name: string;
    version: string;
    description: string;
    auto_start: boolean;
    setup: { required: boolean; label: string };
  };
  tools: ToolDefinition[];
  init: () => void;
  start: () => void;
  stop: () => void;
  onCronTrigger?: (scheduleId: string) => void;
  onSetupStart?: () => SetupStartResult;
  onSetupSubmit?: (args: { stepId: string; values: Record<string, unknown> }) => SetupSubmitResult;
  onSetupCancel?: () => void;
  onOAuthComplete?: (args: OAuthCompleteArgs) => unknown;
  onDisconnect?: () => void;
  publishState?: () => void;
  onOAuthRevoked?: (args: OAuthRevokedArgs) => void;
  onListOptions?: () => { options: SkillOption[] };
  onSetOption?: (args: { name: string; value: unknown }) => void;
  onSessionStart?: (args: { sessionId: string }) => void;
  onSessionEnd?: (args: { sessionId: string }) => void;
  onTick?: () => void;
  onSync?: () => void;
  onPing?: () => PingResult;
  /** Called when the frontend sends load params (e.g. wallet address for wallet skill). */
  onLoad?: (params: Record<string, unknown>) => void;
  onRpc?: (args: { method: string; params: unknown }) => unknown;
  onServerEvent?: (event: string, data: unknown) => void;
  onDisconnect?: () => void;
  /**
   * Called when an unhandled error occurs during async operations
   * (e.g. TDLib auth failures, network errors, promise rejections).
   * Skills should use this to update their state and surface the error to the user.
   */
  onError?: (args: SkillErrorArgs) => void;
}
