-- Mazar Martin CRM — initial Supabase schema (migration 0001)
--
-- Tables + RLS for the three-role multi-tenant model:
--   - 'staff'  → MM employees, full access today (the shared login)
--   - 'agent'  → external real-estate agents, future aggregated/limited views
--   - 'client' → end-buyers, future self-scoped views
--
-- Today only role='staff' is populated. RLS policies for staff are written
-- now; agent/client policies will be added when those features land.
-- Idempotent — safe to re-run.

-- ─────────────────────────────────────────────────────────────────────────
-- Types
-- ─────────────────────────────────────────────────────────────────────────

DO $$ BEGIN
  CREATE TYPE org_role AS ENUM ('staff', 'agent', 'client');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE listing_kind AS ENUM ('forsale', 'offmarket', 'sold');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ─────────────────────────────────────────────────────────────────────────
-- Foundation: orgs + memberships
-- ─────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS orgs (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name       text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS org_members (
  org_id     uuid NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
  user_id    uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  role       org_role NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (org_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_org_members_user ON org_members(user_id);

-- ─────────────────────────────────────────────────────────────────────────
-- is_org_staff: SECURITY DEFINER helper so RLS policies elsewhere can
-- check org_members without recursing into its own RLS.
-- ─────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION is_org_staff(_org_id uuid)
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
  SELECT EXISTS (
    SELECT 1 FROM org_members
    WHERE org_id = _org_id
      AND user_id = auth.uid()
      AND role = 'staff'
  );
$$;

REVOKE EXECUTE ON FUNCTION is_org_staff(uuid) FROM PUBLIC;
GRANT  EXECUTE ON FUNCTION is_org_staff(uuid) TO authenticated;

-- ─────────────────────────────────────────────────────────────────────────
-- Business tables
-- ─────────────────────────────────────────────────────────────────────────

-- Clients (buyers / sellers / leads — the whiteboard records)
CREATE TABLE IF NOT EXISTS clients (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id      uuid NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
  name        text NOT NULL,
  section     text,         -- 'Active Buyer' | 'Pipeline' | 'Settlements' | 'Off Markets' | 'Sellers'
  ba          text,         -- buyer's-agent initials
  referrer    text,
  budget      text,
  spec        text,
  locations   text,
  target      text,
  commission  numeric,
  exp         text,
  status      text,
  notes       text,
  date        text,         -- free-form; matches existing whiteboard schema
  map         text,         -- the MAP field added by feature blocks
  created_by  uuid REFERENCES auth.users(id),
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now(),
  deleted_at  timestamptz   -- soft delete (replaces mmDeletedClients)
);

CREATE INDEX IF NOT EXISTS idx_clients_org      ON clients(org_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_clients_section  ON clients(org_id, section) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_clients_name_ci  ON clients(org_id, lower(name));

-- Comments on a client (mmClientComments)
CREATE TABLE IF NOT EXISTS client_comments (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id  uuid NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  body       text NOT NULL,
  created_by uuid REFERENCES auth.users(id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_client_comments_client
  ON client_comments(client_id, created_at DESC);

-- Activity log on a client (mmClientActivity)
CREATE TABLE IF NOT EXISTS client_activity (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id  uuid NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  kind       text NOT NULL,   -- 'note' | 'status_change' | 'section_change' | ...
  body       jsonb NOT NULL,
  created_by uuid REFERENCES auth.users(id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_client_activity_client
  ON client_activity(client_id, created_at DESC);

-- Comments on a property (mmPropComments) — org-scoped by address
CREATE TABLE IF NOT EXISTS property_comments (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id           uuid NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
  property_address text NOT NULL,
  body             text NOT NULL,
  created_by       uuid REFERENCES auth.users(id),
  created_at       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_property_comments_addr
  ON property_comments(org_id, property_address);

-- Agent call tracking (mmCallStatus + mmCallComments merged)
CREATE TABLE IF NOT EXISTS agent_calls (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id     uuid NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
  agent_key  text NOT NULL,                    -- matches the key the app uses
  called     boolean NOT NULL DEFAULT false,
  voicemail  boolean NOT NULL DEFAULT false,
  comments   jsonb   NOT NULL DEFAULT '[]'::jsonb,
  updated_by uuid REFERENCES auth.users(id),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (org_id, agent_key)
);

-- Saved buyer ↔ property matches (mmSavedMatches)
CREATE TABLE IF NOT EXISTS saved_matches (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id        uuid NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  property_address text NOT NULL,
  suburb           text,
  price            text,
  property_type    text,
  note             text,
  saved_by         uuid REFERENCES auth.users(id),
  saved_at         timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_saved_matches_client
  ON saved_matches(client_id);

-- Dismissed properties per client (mmDismissedProps)
CREATE TABLE IF NOT EXISTS dismissed_props (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id        uuid NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  property_address text NOT NULL,
  dismissed_by     uuid REFERENCES auth.users(id),
  dismissed_at     timestamptz NOT NULL DEFAULT now(),
  UNIQUE (client_id, property_address)
);

-- Properties presented to clients (mmPresented — swipe-deck history)
CREATE TABLE IF NOT EXISTS presented_props (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id        uuid NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  property_address text NOT NULL,
  presented_by     uuid REFERENCES auth.users(id),
  presented_at     timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_presented_client
  ON presented_props(client_id, presented_at DESC);

-- Manually-added listings (mmNewSale, mmNewOff)
CREATE TABLE IF NOT EXISTS manual_listings (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id       uuid NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
  address      text NOT NULL,
  listing_type listing_kind NOT NULL,
  data         jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_by   uuid REFERENCES auth.users(id),
  created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_manual_listings_org
  ON manual_listings(org_id, listing_type);

-- Edits / soft-deletes / blacklist on listings
-- (mmForSaleEdits, mmSoldEdits, mmBlacklist, mmDeletedFS — one table covers all)
CREATE TABLE IF NOT EXISTS listing_edits (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id           uuid NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
  property_address text NOT NULL,
  listing_type     listing_kind NOT NULL,
  edits            jsonb   NOT NULL DEFAULT '{}'::jsonb,
  is_deleted       boolean NOT NULL DEFAULT false,
  is_blacklisted   boolean NOT NULL DEFAULT false,
  updated_by       uuid REFERENCES auth.users(id),
  updated_at       timestamptz NOT NULL DEFAULT now(),
  UNIQUE (org_id, property_address, listing_type)
);

-- ─────────────────────────────────────────────────────────────────────────
-- Per-user UI state — kv pattern, for genuine per-user state only
-- (e.g. mmCommissionUnlocked, mmStatOverrides, mmWeek, caches)
-- ─────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS user_kv (
  user_id    uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  key        text NOT NULL,
  value      jsonb NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, key)
);

-- ─────────────────────────────────────────────────────────────────────────
-- updated_at auto-touch
-- ─────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION touch_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END $$;

DO $$ BEGIN CREATE TRIGGER trg_clients_touch       BEFORE UPDATE ON clients       FOR EACH ROW EXECUTE FUNCTION touch_updated_at(); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TRIGGER trg_agent_calls_touch   BEFORE UPDATE ON agent_calls   FOR EACH ROW EXECUTE FUNCTION touch_updated_at(); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TRIGGER trg_listing_edits_touch BEFORE UPDATE ON listing_edits FOR EACH ROW EXECUTE FUNCTION touch_updated_at(); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TRIGGER trg_user_kv_touch       BEFORE UPDATE ON user_kv       FOR EACH ROW EXECUTE FUNCTION touch_updated_at(); EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ─────────────────────────────────────────────────────────────────────────
-- Row-Level Security
-- ─────────────────────────────────────────────────────────────────────────

ALTER TABLE orgs               ENABLE ROW LEVEL SECURITY;
ALTER TABLE org_members        ENABLE ROW LEVEL SECURITY;
ALTER TABLE clients            ENABLE ROW LEVEL SECURITY;
ALTER TABLE client_comments    ENABLE ROW LEVEL SECURITY;
ALTER TABLE client_activity    ENABLE ROW LEVEL SECURITY;
ALTER TABLE property_comments  ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_calls        ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_matches      ENABLE ROW LEVEL SECURITY;
ALTER TABLE dismissed_props    ENABLE ROW LEVEL SECURITY;
ALTER TABLE presented_props    ENABLE ROW LEVEL SECURITY;
ALTER TABLE manual_listings    ENABLE ROW LEVEL SECURITY;
ALTER TABLE listing_edits      ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_kv            ENABLE ROW LEVEL SECURITY;

-- Drop and recreate policies so the script is re-runnable.
DROP POLICY IF EXISTS "staff_full_orgs"            ON orgs;
DROP POLICY IF EXISTS "staff_read_org_members"     ON org_members;
DROP POLICY IF EXISTS "staff_full_clients"         ON clients;
DROP POLICY IF EXISTS "staff_full_client_comments" ON client_comments;
DROP POLICY IF EXISTS "staff_full_client_activity" ON client_activity;
DROP POLICY IF EXISTS "staff_full_prop_comments"   ON property_comments;
DROP POLICY IF EXISTS "staff_full_agent_calls"     ON agent_calls;
DROP POLICY IF EXISTS "staff_full_saved_matches"   ON saved_matches;
DROP POLICY IF EXISTS "staff_full_dismissed_props" ON dismissed_props;
DROP POLICY IF EXISTS "staff_full_presented_props" ON presented_props;
DROP POLICY IF EXISTS "staff_full_manual_listings" ON manual_listings;
DROP POLICY IF EXISTS "staff_full_listing_edits"   ON listing_edits;
DROP POLICY IF EXISTS "own_user_kv"                ON user_kv;

-- Staff: full access to rows in orgs they belong to as staff.
-- (agent / client roles get NO access yet — those policies arrive when those features do.)

CREATE POLICY "staff_full_orgs" ON orgs
  FOR ALL TO authenticated
  USING      (is_org_staff(id))
  WITH CHECK (is_org_staff(id));

CREATE POLICY "staff_read_org_members" ON org_members
  FOR SELECT TO authenticated
  USING (is_org_staff(org_id));

CREATE POLICY "staff_full_clients" ON clients
  FOR ALL TO authenticated
  USING      (is_org_staff(org_id))
  WITH CHECK (is_org_staff(org_id));

-- Child tables check org membership via the parent client.
CREATE POLICY "staff_full_client_comments" ON client_comments
  FOR ALL TO authenticated
  USING      (EXISTS (SELECT 1 FROM clients c WHERE c.id = client_id AND is_org_staff(c.org_id)))
  WITH CHECK (EXISTS (SELECT 1 FROM clients c WHERE c.id = client_id AND is_org_staff(c.org_id)));

CREATE POLICY "staff_full_client_activity" ON client_activity
  FOR ALL TO authenticated
  USING      (EXISTS (SELECT 1 FROM clients c WHERE c.id = client_id AND is_org_staff(c.org_id)))
  WITH CHECK (EXISTS (SELECT 1 FROM clients c WHERE c.id = client_id AND is_org_staff(c.org_id)));

CREATE POLICY "staff_full_prop_comments" ON property_comments
  FOR ALL TO authenticated
  USING      (is_org_staff(org_id))
  WITH CHECK (is_org_staff(org_id));

CREATE POLICY "staff_full_agent_calls" ON agent_calls
  FOR ALL TO authenticated
  USING      (is_org_staff(org_id))
  WITH CHECK (is_org_staff(org_id));

CREATE POLICY "staff_full_saved_matches" ON saved_matches
  FOR ALL TO authenticated
  USING      (EXISTS (SELECT 1 FROM clients c WHERE c.id = client_id AND is_org_staff(c.org_id)))
  WITH CHECK (EXISTS (SELECT 1 FROM clients c WHERE c.id = client_id AND is_org_staff(c.org_id)));

CREATE POLICY "staff_full_dismissed_props" ON dismissed_props
  FOR ALL TO authenticated
  USING      (EXISTS (SELECT 1 FROM clients c WHERE c.id = client_id AND is_org_staff(c.org_id)))
  WITH CHECK (EXISTS (SELECT 1 FROM clients c WHERE c.id = client_id AND is_org_staff(c.org_id)));

CREATE POLICY "staff_full_presented_props" ON presented_props
  FOR ALL TO authenticated
  USING      (EXISTS (SELECT 1 FROM clients c WHERE c.id = client_id AND is_org_staff(c.org_id)))
  WITH CHECK (EXISTS (SELECT 1 FROM clients c WHERE c.id = client_id AND is_org_staff(c.org_id)));

CREATE POLICY "staff_full_manual_listings" ON manual_listings
  FOR ALL TO authenticated
  USING      (is_org_staff(org_id))
  WITH CHECK (is_org_staff(org_id));

CREATE POLICY "staff_full_listing_edits" ON listing_edits
  FOR ALL TO authenticated
  USING      (is_org_staff(org_id))
  WITH CHECK (is_org_staff(org_id));

-- Per-user kv: each user reads/writes only their own rows.
CREATE POLICY "own_user_kv" ON user_kv
  FOR ALL TO authenticated
  USING      (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

-- ─────────────────────────────────────────────────────────────────────────
-- Seed: ensure the Mazar Martin org exists and the shared user is staff.
-- (Idempotent — safe to re-run.)
-- ─────────────────────────────────────────────────────────────────────────

DO $$
DECLARE
  v_org_id  uuid;
  v_user_id uuid;
BEGIN
  SELECT id INTO v_user_id
  FROM auth.users
  WHERE email = 'mazarmartinapp@gmail.com'
  LIMIT 1;

  IF v_user_id IS NULL THEN
    RAISE NOTICE 'shared user mazarmartinapp@gmail.com not found yet — skipping seed';
    RETURN;
  END IF;

  SELECT id INTO v_org_id FROM orgs WHERE name = 'Mazar Martin' LIMIT 1;
  IF v_org_id IS NULL THEN
    INSERT INTO orgs (name) VALUES ('Mazar Martin') RETURNING id INTO v_org_id;
  END IF;

  INSERT INTO org_members (org_id, user_id, role)
  VALUES (v_org_id, v_user_id, 'staff')
  ON CONFLICT (org_id, user_id) DO NOTHING;
END $$;
