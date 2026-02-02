-- PostgreSQL schema (v1.2)

create table if not exists ticker_universe (
  symbol                text primary key,
  company_name_en       text not null,
  universe              text not null check (universe in ('sp500','nasdaq_composite','both')),
  sector_id             text,
  sector_name_en        text,
  industry_name_en      text,
  is_active             boolean not null default true,
  updated_at            timestamptz not null default now()
);

create table if not exists market_bucket (
  market_id     text primary key,
  label_en      text not null,
  sort_order    int not null default 0,
  is_active     boolean not null default true
);

create table if not exists cluster_market_impact (
  cluster_id           text not null,
  market_id            text not null references market_bucket(market_id),
  expected_direction   text not null,
  magnitude            double precision not null check (magnitude >= 0 and magnitude <= 1),
  confidence           double precision not null check (confidence >= 0 and confidence <= 1),
  horizon              text not null,
  channels             jsonb not null default '[]'::jsonb,
  rationale_en         text not null,
  created_at           timestamptz not null default now(),
  primary key (cluster_id, market_id)
);

create table if not exists cluster_sector_impact (
  cluster_id           text not null,
  sector_id            text not null,
  sector_name_en       text not null,
  expected_direction   text not null,
  impact_score         double precision not null check (impact_score >= 0 and impact_score <= 100),
  confidence           double precision not null check (confidence >= 0 and confidence <= 1),
  horizon              text not null,
  channels             jsonb not null default '[]'::jsonb,
  rationale_en         text not null,
  created_at           timestamptz not null default now(),
  primary key (cluster_id, sector_id)
);

create table if not exists cluster_ticker_impact (
  cluster_id               text not null,
  symbol                   text not null references ticker_universe(symbol),
  expected_direction       text not null,
  expected_return_bps      double precision not null check (expected_return_bps >= -5000 and expected_return_bps <= 5000),
  expected_vol_delta       double precision not null check (expected_vol_delta >= -5 and expected_vol_delta <= 5),
  confidence               double precision not null check (confidence >= 0 and confidence <= 1),
  horizon                  text not null,
  drivers                  jsonb not null default '[]'::jsonb,
  rationale_en             text not null,
  realized_return_bps      double precision,
  realized_window          text,
  realized_measured_at     timestamptz,
  created_at               timestamptz not null default now(),
  primary key (cluster_id, symbol)
);

create table if not exists topic_index_intraday (
  ts            timestamptz not null,
  topic_id      text not null,
  topic_name_en text not null,
  index_value   double precision not null,
  sentiment     text not null,
  news_volume   int not null default 0,
  primary key (ts, topic_id)
);

create table if not exists calibration_ledger (
  ledger_id            bigserial primary key,
  cluster_id           text not null,
  symbol               text,
  event_type           text not null,
  horizon              text not null,
  predicted_return_bps double precision,
  predicted_confidence double precision,
  realized_return_bps  double precision,
  realized_window      text,
  regime_label         text,
  created_at           timestamptz not null default now()
);
