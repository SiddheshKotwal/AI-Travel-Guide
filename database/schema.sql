create table users (
    id uuid primary key default uuid_generate_v4(),
    email text unique not null,
    hashed_password text not null,
    full_name text,
    travel_preferences jsonb,
    created_at timestamp with time zone default timezone('utc'::text, now())
);
