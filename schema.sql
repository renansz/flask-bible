drop table if exists entries;
create table entries (
       id integer primary key autoincrement,
       book_id integer not null,
       chapter integer not null,
       verse integer not null,
       text text not null
);
