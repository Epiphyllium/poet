import { integer, real, sqliteTable, text } from 'drizzle-orm/sqlite-core';

export const traces = sqliteTable('traces', {
  id: text('id').primaryKey(), topic: text('topic').notNull(), model: text('model').notNull(),
  startedAt: text('started_at').notNull(), status: text('status').notNull(), source: text('source').notNull(),
  durationMs: real('duration_ms').notNull(), promptTokens: integer('prompt_tokens').notNull(),
  completionTokens: integer('completion_tokens').notNull(), totalTokens: integer('total_tokens').notNull(),
  cost: real('cost').notNull(), resultJson: text('result_json').notNull(), eventsJson: text('events_json').notNull(),
});
