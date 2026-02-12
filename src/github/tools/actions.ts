// Actions & Workflows tools (9 tools)
import { ghGet, ghPost } from '../api';
import {
  optNumber,
  optString,
  reqString,
  truncate,
  validatePositiveInt,
  validateRepoSpec,
} from '../helpers';

interface GitHubWorkflow {
  id?: number;
  name?: string;
  state?: string;
  path?: string;
}

interface GitHubWorkflowRunsResponse {
  workflow_runs?: GitHubWorkflowRun[];
}

interface GitHubWorkflowRun {
  run_number?: number;
  name?: string;
  conclusion?: string;
  status?: string;
  head_branch?: string;
  created_at?: string;
}

interface GitHubJobsResponse {
  jobs?: {
    name?: string;
    conclusion?: string;
    status?: string;
    steps?: { name?: string; conclusion?: string; status?: string }[];
  }[];
}

export const listWorkflowsTool: ToolDefinition = {
  name: 'list-workflows',
  description: 'List GitHub Actions workflows defined in a repository',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
    },
    required: ['owner', 'repo'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const r = (await ghGet(`/repos/${spec}/actions/workflows`)) as {
        workflows?: GitHubWorkflow[];
      };
      const workflows = r.workflows ?? [];

      if (!workflows.length) return JSON.stringify({ message: `No workflows in ${spec}.` });

      const lines = workflows.slice(0, 30).map(w => {
        const wfState = w.state ?? '';
        return `${w.name ?? '(unnamed)'} (id: ${w.id ?? '?'}) [${wfState}] - ${w.path ?? ''}`;
      });
      return JSON.stringify({ workflows: lines.join('\n') });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const listWorkflowRunsTool: ToolDefinition = {
  name: 'list-workflow-runs',
  description: 'List recent workflow runs for a repository',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      limit: { type: 'number', description: 'Maximum number of runs to return' },
      workflow_id: {
        type: 'string',
        description: "Filter by workflow ID or filename (e.g. 'ci.yml')",
      },
      branch: { type: 'string', description: 'Filter by branch name' },
      status: {
        type: 'string',
        description: 'Filter by status',
        enum: ['queued', 'in_progress', 'completed', 'waiting', 'requested'],
      },
    },
    required: ['owner', 'repo'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const limit = optNumber(args, 'limit', 20);
      const workflowId = optString(args, 'workflow_id');
      const branch = optString(args, 'branch');
      const status = optString(args, 'status');

      let endpoint: string;
      if (workflowId) {
        endpoint = `/repos/${spec}/actions/workflows/${encodeURIComponent(
          workflowId
        )}/runs?per_page=${limit}`;
      } else {
        endpoint = `/repos/${spec}/actions/runs?per_page=${limit}`;
      }
      if (branch) endpoint += `&branch=${encodeURIComponent(branch)}`;
      if (status) endpoint += `&status=${status}`;

      const r = (await ghGet(endpoint)) as GitHubWorkflowRunsResponse;
      const runs = r.workflow_runs ?? [];

      if (!runs.length) return JSON.stringify({ message: 'No workflow runs found.' });

      const lines = runs.slice(0, limit).map(run => {
        const conclusion = run.conclusion ?? run.status ?? 'in_progress';
        const branchName = run.head_branch ?? '';
        return `#${run.run_number ?? '?'} ${run.name ?? '(unnamed)'} [${conclusion}] on ${branchName} (${
          run.created_at ?? ''
        })`;
      });
      return JSON.stringify({ runs: lines.join('\n'), count: lines.length });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const getWorkflowRunTool: ToolDefinition = {
  name: 'get-workflow-run',
  description: 'Get detailed information about a specific workflow run',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      run_id: { type: 'number', description: 'Workflow run ID' },
    },
    required: ['owner', 'repo', 'run_id'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const runId = validatePositiveInt(args.run_id, 'run_id');
      const run = (await ghGet(`/repos/${spec}/actions/runs/${runId}`)) as {
        run_number?: number;
        name?: string;
        status?: string;
        conclusion?: string;
        head_branch?: string;
        event?: string;
        head_sha?: string;
        html_url?: string;
        created_at?: string;
        updated_at?: string;
        run_started_at?: string;
      };

      const lines = [
        `Run #${run.run_number}: ${run.name}`,
        `Status: ${run.status}`,
        `Conclusion: ${run.conclusion || 'N/A'}`,
        `Branch: ${run.head_branch}`,
        `Event: ${run.event}`,
        `SHA: ${run.head_sha?.substring(0, 7)}`,
        `URL: ${run.html_url}`,
        `Created: ${run.created_at}`,
        `Updated: ${run.updated_at}`,
      ];
      if (run.run_started_at) lines.push(`Started: ${run.run_started_at}`);
      return JSON.stringify({ info: lines.join('\n') });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const listRunJobsTool: ToolDefinition = {
  name: 'list-run-jobs',
  description: 'List jobs for a specific workflow run',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      run_id: { type: 'number', description: 'Workflow run ID' },
    },
    required: ['owner', 'repo', 'run_id'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const runId = validatePositiveInt(args.run_id, 'run_id');
      const r = (await ghGet(`/repos/${spec}/actions/runs/${runId}/jobs`)) as GitHubJobsResponse;
      const jobs = r.jobs ?? [];

      if (!jobs.length) return JSON.stringify({ message: `No jobs in run #${runId}.` });

      const lines: string[] = [];
      for (const j of jobs) {
        const conclusion = j.conclusion ?? j.status ?? 'in_progress';
        lines.push(`${j.name ?? '(job)'} [${conclusion}]`);
        if (j.steps) {
          for (const s of j.steps) {
            const stepStatus = s.conclusion ?? s.status ?? '?';
            lines.push(`  - ${s.name ?? '(step)'} [${stepStatus}]`);
          }
        }
      }
      return JSON.stringify({ jobs: lines.join('\n') });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const getRunLogsTool: ToolDefinition = {
  name: 'get-run-logs',
  description: 'Get the logs URL for a specific workflow run',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      run_id: { type: 'number', description: 'Workflow run ID' },
    },
    required: ['owner', 'repo', 'run_id'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const runId = validatePositiveInt(args.run_id, 'run_id');
      const run = (await ghGet(`/repos/${spec}/actions/runs/${runId}`)) as {
        run_number?: number;
        conclusion?: string;
        status?: string;
      };
      const logsUrl = `https://github.com/${spec}/actions/runs/${runId}`;
      return JSON.stringify({
        message: `Run #${run.run_number} (${run.conclusion || run.status})\nView logs at: ${logsUrl}`,
      });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const rerunWorkflowTool: ToolDefinition = {
  name: 'rerun-workflow',
  description: 'Re-run an entire workflow run',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      run_id: { type: 'number', description: 'Workflow run ID to re-run' },
    },
    required: ['owner', 'repo', 'run_id'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const runId = validatePositiveInt(args.run_id, 'run_id');
      await ghPost(`/repos/${spec}/actions/runs/${runId}/rerun`);
      return JSON.stringify({ message: `Workflow run #${runId} rerun initiated.` });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const cancelWorkflowRunTool: ToolDefinition = {
  name: 'cancel-workflow-run',
  description: 'Cancel a workflow run that is in progress',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      run_id: { type: 'number', description: 'Workflow run ID to cancel' },
    },
    required: ['owner', 'repo', 'run_id'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const runId = validatePositiveInt(args.run_id, 'run_id');
      await ghPost(`/repos/${spec}/actions/runs/${runId}/cancel`);
      return JSON.stringify({ message: `Workflow run #${runId} cancelled.` });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const triggerWorkflowTool: ToolDefinition = {
  name: 'trigger-workflow',
  description: 'Manually trigger a workflow dispatch event',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      workflow_id: { type: 'string', description: "Workflow ID or filename (e.g. 'deploy.yml')" },
      ref: { type: 'string', description: 'Git ref (branch or tag) to run the workflow on' },
      inputs: {
        type: 'object',
        description: 'Input key-value pairs for the workflow_dispatch event',
      },
    },
    required: ['owner', 'repo', 'workflow_id'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const workflowId = reqString(args, 'workflow_id');
      const ref = optString(args, 'ref') || 'main';
      const inputs = args.inputs && typeof args.inputs === 'object' ? args.inputs : {};

      await ghPost(
        `/repos/${spec}/actions/workflows/${encodeURIComponent(workflowId)}/dispatches`,
        { ref, inputs }
      );
      return JSON.stringify({ message: `Workflow '${workflowId}' triggered on ${ref}.` });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const viewWorkflowYamlTool: ToolDefinition = {
  name: 'view-workflow-yaml',
  description: 'View the YAML source of a workflow definition',
  input_schema: {
    type: 'object',
    properties: {
      owner: { type: 'string', description: 'Repository owner' },
      repo: { type: 'string', description: 'Repository name' },
      workflow_id: { type: 'string', description: "Workflow ID or filename (e.g. 'ci.yml')" },
    },
    required: ['owner', 'repo', 'workflow_id'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const spec = validateRepoSpec(args);
      const workflowId = reqString(args, 'workflow_id');

      // Get workflow details to find the file path
      const wf = (await ghGet(
        `/repos/${spec}/actions/workflows/${encodeURIComponent(workflowId)}`
      )) as any;
      const path = wf.path;

      // Get the file content
      const content = (await ghGet(`/repos/${spec}/contents/${encodeURIComponent(path)}`)) as any;
      if (content.encoding === 'base64' && content.content) {
        const decoded = atob(content.content.replace(/\n/g, ''));
        return JSON.stringify({ yaml: `--- ${path} ---\n${truncate(decoded)}` });
      }
      return JSON.stringify({ yaml: '(empty workflow file)' });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const actionsTools: ToolDefinition[] = [
  listWorkflowsTool,
  listWorkflowRunsTool,
  getWorkflowRunTool,
  listRunJobsTool,
  getRunLogsTool,
  rerunWorkflowTool,
  cancelWorkflowRunTool,
  triggerWorkflowTool,
  viewWorkflowYamlTool,
];
