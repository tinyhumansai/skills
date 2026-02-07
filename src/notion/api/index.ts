// Barrel export for the Notion API layer.
// Re-exports all domain modules and creates a unified notionApi object.
import * as blocks from './blocks';
import * as comments from './comments';
import * as databases from './databases';
import * as pages from './pages';
import * as search from './search';
import * as users from './users';

export { blocks, comments, databases, pages, search, users };

export const notionApi = { ...pages, ...databases, ...blocks, ...users, ...comments, ...search };

export type NotionApi = typeof notionApi;
