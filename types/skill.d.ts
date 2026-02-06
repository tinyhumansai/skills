interface Skill {
  info: {
    id: string;
    name: string;
    runtime: string;
    entry: string;
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
  onListOptions?: () => { options: SkillOption[] };
  onSetOption?: (args: { name: string; value: unknown }) => void;
  onSessionStart?: (args: { sessionId: string }) => void;
  onSessionEnd?: (args: { sessionId: string }) => void;
  onTick?: () => void;
  /** Called when the frontend sends load params (e.g. wallet address for wallet skill). */
  onLoad?: (params: Record<string, unknown>) => void;
  onRpc?: (args: { method: string; params: unknown }) => unknown;
  onServerEvent?: (event: string, data: unknown) => void;
  onDisconnect?: () => void;
}
