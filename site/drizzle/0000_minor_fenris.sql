CREATE TABLE `traces` (
	`id` text PRIMARY KEY NOT NULL,
	`topic` text NOT NULL,
	`model` text NOT NULL,
	`started_at` text NOT NULL,
	`status` text NOT NULL,
	`source` text NOT NULL,
	`duration_ms` real NOT NULL,
	`prompt_tokens` integer NOT NULL,
	`completion_tokens` integer NOT NULL,
	`total_tokens` integer NOT NULL,
	`cost` real NOT NULL,
	`result_json` text NOT NULL,
	`events_json` text NOT NULL
);
