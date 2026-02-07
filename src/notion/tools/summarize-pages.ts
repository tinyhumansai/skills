// Tool: notion-summarize-pages
// Triggers AI summarization of synced pages and returns results
import '../skill-state';

export const summarizePagesTool: ToolDefinition = {
  name: 'notion-summarize-pages',
  description:
    'Run AI summarization on synced Notion pages that have content but no summary (or stale summaries). ' +
    'Requires a local model to be available. Returns count of pages summarized.',
  input_schema: {
    type: 'object',
    properties: {
      limit: {
        type: 'number',
        description:
          'Maximum number of pages to summarize in this batch. Defaults to the configured maxPagesPerContentSync.',
      },
    },
  },
  execute(args: Record<string, unknown>): string {
    try {
      if (!oauth.getCredential()) {
        return JSON.stringify({
          success: false,
          error: 'Notion not connected. Complete OAuth setup first.',
        });
      }

      if (!model.isAvailable()) {
        return JSON.stringify({
          success: false,
          error: 'AI model not available. Ensure a local model is downloaded and loaded.',
          model_status: model.getStatus(),
        });
      }

      const s = globalThis.getNotionSkillState();
      const batchLimit =
        typeof args.limit === 'number' && args.limit > 0
          ? args.limit
          : s.config.maxPagesPerContentSync;

      const getPagesNeedingSummary = (globalThis as Record<string, unknown>)
        .getPagesNeedingSummary as
        | ((
            limit: number
          ) => Array<{
            id: string;
            title: string;
            content_text: string;
            url: string | null;
            last_edited_time: string;
            created_time: string;
          }>)
        | undefined;
      const updatePageAiSummary = (globalThis as Record<string, unknown>).updatePageAiSummary as
        | ((
            pageId: string,
            summary: string,
            opts?: {
              category?: string;
              sentiment?: string;
              entities?: unknown[];
              topics?: string[];
            }
          ) => void)
        | undefined;
      const inferClassification = (globalThis as Record<string, unknown>).inferClassification as
        | ((text: string) => {
            category: string;
            sentiment: string;
            entities: Array<{ id: string; type: string; name?: string; role?: string }>;
            topics: string[];
          })
        | undefined;
      const getPageStructuredEntities = (globalThis as Record<string, unknown>)
        .getPageStructuredEntities as
        | ((
            pageId: string
          ) => Array<{ id: string; type: string; name?: string; role: string; property?: string }>)
        | undefined;
      const mergeEntitiesFn = (globalThis as Record<string, unknown>).mergeEntities as
        | ((structured: unknown[], llm: unknown[]) => unknown[])
        | undefined;

      if (!getPagesNeedingSummary || !updatePageAiSummary) {
        return JSON.stringify({ success: false, error: 'Database helpers not available.' });
      }

      const pages = getPagesNeedingSummary(batchLimit);

      if (pages.length === 0) {
        return JSON.stringify({
          success: true,
          message: 'All pages are already summarized.',
          summarized: 0,
          failed: 0,
        });
      }

      let summarized = 0;
      let failed = 0;
      const errors: string[] = [];

      let titleOnly = 0;

      for (const page of pages) {
        try {
          const trimmed = page.content_text.trim();
          const hasContent = trimmed.length >= 50;

          // Classify: category, sentiment, entities, topics — all in one LLM call
          const classifyInput = hasContent
            ? `Title: ${page.title}\nContent: ${trimmed.substring(0, 1000)}`
            : `Title: ${page.title}`;
          const classification = inferClassification
            ? inferClassification(classifyInput)
            : { category: 'other', sentiment: 'neutral', entities: [], topics: [] };

          let summary: string;

          if (!hasContent) {
            summary = page.title;
            titleOnly++;
          } else {
            const metaParts: string[] = [`Title: ${page.title}`];
            if (page.url) metaParts.push(`URL: ${page.url}`);
            metaParts.push(`Created: ${page.created_time}`);
            metaParts.push(`Last edited: ${page.last_edited_time}`);
            const metaBlock = metaParts.join('\n');

            const summarizeFn = (globalThis as Record<string, unknown>).summarizeWithFallback as
              | ((content: string, metaBlock: string) => string | null)
              | undefined;
            const result = summarizeFn ? summarizeFn(trimmed, metaBlock) : null;
            if (!result) continue;
            summary = result;
          }

          // Merge structured entities (from Notion properties) with LLM-inferred entities
          const structuredEnts = getPageStructuredEntities?.(page.id) ?? [];
          const mergedEntities = mergeEntitiesFn
            ? (mergeEntitiesFn(structuredEnts, classification.entities) as Array<{
                id: string;
                type: string;
                name?: string;
                role: string;
              }>)
            : [
                ...structuredEnts,
                ...classification.entities.map(e => ({ ...e, role: e.role || 'mentioned' })),
              ];

          // Store summary + classification in local DB
          updatePageAiSummary(page.id, summary, {
            category: classification.category,
            sentiment: classification.sentiment,
            entities: mergedEntities,
            topics: classification.topics,
          });

          // Submit to server via socket
          model.submitSummary({
            summary,
            category: classification.category,
            dataSource: 'notion',
            sentiment: classification.sentiment as 'positive' | 'neutral' | 'negative' | 'mixed',
            keyPoints: classification.topics.length > 0 ? classification.topics : undefined,
            entities:
              mergedEntities.length > 0
                ? mergedEntities.map(e => ({
                    id: e.id,
                    type: (e.type === 'page' ? 'other' : e.type) as
                      | 'person'
                      | 'wallet'
                      | 'channel'
                      | 'group'
                      | 'organization'
                      | 'token'
                      | 'other',
                    name: e.name,
                    role: e.role,
                  }))
                : undefined,
            metadata: {
              pageId: page.id,
              pageTitle: page.title,
              pageUrl: page.url,
              lastEditedTime: page.last_edited_time,
              createdTime: page.created_time,
              contentLength: trimmed.length,
              noContent: !hasContent,
            },
            createdAt: new Date(page.created_time).toISOString(),
            updatedAt: new Date(page.last_edited_time).toISOString(),
          });

          summarized++;
        } catch (e) {
          failed++;
          errors.push(`${page.title}: ${e instanceof Error ? e.message : String(e)}`);
        }
      }

      return JSON.stringify({
        success: true,
        summarized,
        failed,
        title_only: titleOnly,
        total_candidates: pages.length,
        errors: errors.length > 0 ? errors : undefined,
      });
    } catch (e) {
      return JSON.stringify({ success: false, error: e instanceof Error ? e.message : String(e) });
    }
  },
};
