/** get-status tool — returns current skill status, config summary, and error count */
import '../skill-state';

export const getStatusTool: ToolDefinition = {
  name: 'get-status',
  description: 'Get current skill status including configuration summary and error count.',
  input_schema: {
    type: 'object',
    properties: {
      verbose: {
        type: 'string',
        enum: ['true', 'false'],
        description: 'Include full config in response (default: false)',
      },
    },
  },
  execute(args: Record<string, unknown>): string {
    const s = globalThis.getSkillState();
    const verbose = args.verbose === 'true';

    const result: Record<string, unknown> = {
      status: s.isRunning ? 'running' : 'stopped',
      fetchCount: s.fetchCount,
      errorCount: s.errorCount,
      lastFetchTime: s.lastFetchTime,
      refreshInterval: s.config.refreshInterval,
      platform: platform.os(),
    };

    if (verbose)
      result.config = {
        serverUrl: s.config.serverUrl,
        refreshInterval: s.config.refreshInterval,
        notifyOnError: s.config.notifyOnError,
        verbose: s.config.verbose,
      };

    return JSON.stringify(result);
  },
};
