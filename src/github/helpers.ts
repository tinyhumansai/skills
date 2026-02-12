// Validation and formatting helpers for GitHub skill

const USERNAME_RE = /^[a-zA-Z0-9](?:[a-zA-Z0-9._-]*[a-zA-Z0-9])?$/;

export function reqString(args: Record<string, unknown>, key: string): string {
  const v = args[key];
  if (typeof v !== 'string' || !v.trim()) {
    throw new Error(`Missing required parameter: ${key}`);
  }
  return v.trim();
}

export function optString(args: Record<string, unknown>, key: string): string | null {
  const v = args[key];
  if (typeof v === 'string' && v.trim()) {
    return v.trim();
  }
  return null;
}

export function optNumber(args: Record<string, unknown>, key: string, fallback: number): number {
  const v = args[key];
  if (typeof v === 'number') return Math.floor(v);
  if (typeof v === 'string') {
    const n = parseInt(v, 10);
    if (!isNaN(n)) return n;
  }
  return fallback;
}

export function optBoolean(args: Record<string, unknown>, key: string, fallback: boolean): boolean {
  const v = args[key];
  return typeof v === 'boolean' ? v : fallback;
}

export function optStringList(args: Record<string, unknown>, key: string): string[] {
  const v = args[key];
  if (Array.isArray(v)) {
    return v.map(item => String(item).trim()).filter(Boolean);
  }
  if (typeof v === 'string' && v.trim()) {
    return v
      .split(',')
      .map(s => s.trim())
      .filter(Boolean);
  }
  return [];
}

export function validateOwnerRepo(args: Record<string, unknown>): { owner: string; repo: string } {
  const owner = reqString(args, 'owner');
  const repo = reqString(args, 'repo');
  if (!USERNAME_RE.test(owner)) {
    throw new Error(`Invalid owner: '${owner}'`);
  }
  return { owner, repo };
}

export function validateRepoSpec(args: Record<string, unknown>): string {
  const { owner, repo } = validateOwnerRepo(args);
  return `${owner}/${repo}`;
}

export function validateUsername(value: string): string {
  const v = value.trim().replace(/^@/, '');
  if (!v || !USERNAME_RE.test(v)) {
    throw new Error(`Invalid GitHub username: '${v}'`);
  }
  return v;
}

export function validatePositiveInt(value: unknown, paramName: string): number {
  if (typeof value === 'number') {
    const iv = Math.floor(value);
    if (iv <= 0) throw new Error(`Invalid ${paramName}: must be a positive integer.`);
    return iv;
  }
  if (typeof value === 'string') {
    const iv = parseInt(value, 10);
    if (isNaN(iv) || iv <= 0) throw new Error(`Invalid ${paramName}: must be a positive integer.`);
    return iv;
  }
  throw new Error(`Invalid ${paramName}: must be a positive integer.`);
}

export function truncate(text: string, maxLen: number = 4000): string {
  if (text.length <= maxLen) return text;
  return text.substring(0, maxLen - 20) + '\n... (truncated)';
}
