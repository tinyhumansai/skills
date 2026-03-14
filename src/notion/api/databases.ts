// Notion Databases API
import type {
  CreateDatabaseResponse,
  GetDatabaseResponse,
  GetDataSourceResponse,
  QueryDataSourceResponse,
  SearchResponse,
  UpdateDatabaseResponse,
} from '@notionhq/client/build/src/api-endpoints';

import {
  detectApiVersion,
  formatApiError,
  getQueryEndpoint,
  resolveDataSourceId,
} from '../helpers';
import { apiFetch } from './client';

export function getDatabase(databaseId: string): Promise<GetDatabaseResponse> {
  return apiFetch<GetDatabaseResponse>(`/databases/${databaseId}`);
}

/**
 * Resolve a database container ID to its first data_source ID.
 * This is needed because the Notion API 2025-09-03 uses data_sources
 * for queries and schema access. Now uses the helper function for better compatibility.
 */
export async function resolveDataSourceIdCompat(databaseId: string): Promise<string> {
  try {
    return await resolveDataSourceId(databaseId);
  } catch (error) {
    throw new Error(
      `Database has no data sources or is not accessible. Share the database with your integration. ${formatApiError(error)}`
    );
  }
}

export function getDataSource(dataSourceId: string): Promise<GetDataSourceResponse> {
  return apiFetch<GetDataSourceResponse>(`/data_sources/${dataSourceId}`);
}

/**
 * Query a database with automatic API version detection and endpoint resolution.
 * Handles both legacy database queries and new data source queries seamlessly.
 * Provides automatic fallback for maximum compatibility.
 */
export async function queryDataSource(
  databaseId: string,
  body?: Record<string, unknown>
): Promise<QueryDataSourceResponse> {
  const apiVersion = await detectApiVersion();
  const requestBody = body || {};

  try {
    // Get the appropriate endpoint for the current API version
    const endpoint = await getQueryEndpoint(databaseId);

    console.log(`[notion][databases] Querying ${endpoint} with API version ${apiVersion}`);

    return await apiFetch<QueryDataSourceResponse>(endpoint, {
      method: 'POST',
      body: requestBody,
      apiVersion,
    });
  } catch (error) {
    const errorMessage = String(error);

    // If new API fails with version/endpoint errors, try legacy fallback
    if (
      apiVersion !== '2022-06-28' &&
      (errorMessage.includes('invalid_version') ||
        errorMessage.includes('data_source') ||
        errorMessage.includes('404'))
    ) {
      console.log(
        `[notion][databases] New API failed, attempting legacy fallback for database ${databaseId}`
      );

      try {
        return await apiFetch<QueryDataSourceResponse>(`/databases/${databaseId}/query`, {
          method: 'POST',
          body: requestBody,
          apiVersion: '2022-06-28',
        });
      } catch (fallbackError) {
        console.error(`[notion][databases] Legacy fallback also failed:`, fallbackError);
        throw new Error(
          `Failed to query database with both new and legacy APIs: ${formatApiError(fallbackError)}`
        );
      }
    }

    // Re-throw the original error if it's not a version-related issue
    throw error;
  }
}

/**
 * Create a database with API version compatibility.
 */
export async function createDatabase(
  body: Record<string, unknown>
): Promise<CreateDatabaseResponse> {
  const apiVersion = await detectApiVersion();
  return apiFetch<CreateDatabaseResponse>('/databases', { method: 'POST', body, apiVersion });
}

/**
 * Update a database with API version compatibility.
 */
export async function updateDatabase(
  databaseId: string,
  body: Record<string, unknown>
): Promise<UpdateDatabaseResponse> {
  const apiVersion = await detectApiVersion();
  return apiFetch<UpdateDatabaseResponse>(`/databases/${databaseId}`, {
    method: 'PATCH',
    body,
    apiVersion,
  });
}

/**
 * List all databases with API version compatibility.
 * Uses data_source filter for new API, database filter for legacy API.
 */
export async function listAllDatabases(pageSize: number = 20): Promise<SearchResponse> {
  const apiVersion = await detectApiVersion();

  // Use appropriate filter based on API version
  const filter =
    apiVersion === '2025-09-03'
      ? { property: 'object', value: 'data_source' }
      : { property: 'object', value: 'database' };

  try {
    return await apiFetch<SearchResponse>('/search', {
      method: 'POST',
      body: { filter, page_size: pageSize },
      apiVersion,
    });
  } catch (error) {
    // If new API search fails, try legacy database search
    if (apiVersion !== '2022-06-28') {
      console.log(`[notion][databases] New API search failed, trying legacy database search`);
      return await apiFetch<SearchResponse>('/search', {
        method: 'POST',
        body: { filter: { property: 'object', value: 'database' }, page_size: pageSize },
        apiVersion: '2022-06-28',
      });
    }
    throw error;
  }
}
