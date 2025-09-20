create table if not exists arxiv_paper (
  id integer primary key generated always as identity,
  title text not null,
  abstract text not null,
  authors text[],
  url text not null,
  paper_id text not null,
  sections jsonb not null,
  created_at timestamp with time zone default now() not null,
  updated_at timestamp with time zone default now() not null
);

create extension if not exists moddatetime schema extensions;
create trigger handle_project_updated_at before update on arxiv_paper
  for each row execute procedure moddatetime (updated_at);
