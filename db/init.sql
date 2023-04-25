CREATE DATABASE historical_prices;

\c historical_prices;

CREATE TABLE stock_data (
    id SERIAL PRIMARY KEY,
    bar_number INTEGER NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    interval VARCHAR(10) NOT NULL,
    open NUMERIC(15, 4),
    high NUMERIC(15, 4),
    low NUMERIC(15, 4),
    close NUMERIC(15, 4)
);

CREATE TABLE timestamp_data (
    id SERIAL PRIMARY KEY,
    bar_number INTEGER NOT NULL,
    interval VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    UNIQUE (bar_number, interval)
);
