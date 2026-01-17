alter table arxiv_paper add column if not exists
  target_date date not null default '2025-10-20'
  status varchar(100) not null default 'initialized';
