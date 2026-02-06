// Simple test skill - no external modules, TypeScript with bridge APIs (store, state, tools).

interface SimpleSkillConfig {
  greeting: string;
  count: number;
}

const CONFIG: SimpleSkillConfig = { greeting: 'Hello', count: 0 };

function init(): void {
  console.log('[simple-skill] Initializing');
  const saved = store.get('config') as Partial<SimpleSkillConfig> | null;
  if (saved) {
    CONFIG.greeting = saved.greeting ?? CONFIG.greeting;
    CONFIG.count = saved.count ?? CONFIG.count;
  }
  console.log('[simple-skill] Config loaded: ' + CONFIG.greeting);
}

function start(): void {
  console.log('[simple-skill] Starting');
  state.set('status', 'running');
}

function stop(): void {
  console.log('[simple-skill] Stopping');
  store.set('config', CONFIG);
  state.set('status', 'stopped');
}

function onSetupStart(): SetupStartResult {
  return {
    step: {
      id: 'greeting',
      title: 'Configure Greeting',
      description: 'Set your custom greeting message',
      fields: [
        { name: 'greeting', type: 'text', label: 'Greeting', required: true, default: 'Hello' },
      ],
    },
  };
}

function onSetupSubmit(args: {
  stepId: string;
  values: Record<string, unknown>;
}): SetupSubmitResult {
  const { stepId, values } = args;

  if (stepId === 'greeting') {
    CONFIG.greeting = (values.greeting as string) || 'Hello';
    store.set('config', CONFIG);
    return { status: 'complete' };
  }

  return { status: 'error', errors: [{ field: '', message: 'Unknown step' }] };
}

const tools: ToolDefinition[] = [
  {
    name: 'greet',
    description: 'Returns a greeting message',
    input_schema: {
      type: 'object',
      properties: { name: { type: 'string', description: 'Name to greet' } },
    },
    execute(args: Record<string, unknown>): string {
      CONFIG.count++;
      const name = (args.name as string) || 'World';
      return JSON.stringify({ message: CONFIG.greeting + ', ' + name + '!', count: CONFIG.count });
    },
  },
  {
    name: 'get-count',
    description: 'Get the greeting count',
    input_schema: { type: 'object', properties: {} },
    execute(): string {
      return JSON.stringify({ count: CONFIG.count });
    },
  },
];

interface Skill {
  info: SkillInfo;
  tools: ToolDefinition[];
  init: () => void;
  start: () => void;
  stop: () => void;
  onSetupStart: () => SetupStartResult;
  onSetupSubmit: (args: { stepId: string; values: Record<string, unknown> }) => SetupSubmitResult;
}

const skill: Skill = {
  info: { id: 'simple-skill', name: 'Simple Test Skill', version: '1.0.0' },
  tools,
  init,
  start,
  stop,
  onSetupStart,
  onSetupSubmit,
};

export default skill;
