-- Migration 0002 — support for mmClientEdits
--
-- Adds an `edits` JSONB column to `clients` to hold the sparse per-client
-- override map that the app's existing render code expects, and a UNIQUE
-- constraint on (org_id, name) so the adapter can upsert by client name.
-- Idempotent — safe to re-run.

ALTER TABLE clients
  ADD COLUMN IF NOT EXISTS edits jsonb NOT NULL DEFAULT '{}'::jsonb;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'clients_org_name_unique'
  ) THEN
    ALTER TABLE clients ADD CONSTRAINT clients_org_name_unique UNIQUE (org_id, name);
  END IF;
END $$;
