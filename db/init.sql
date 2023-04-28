CREATE DATABASE historical_prices;

\c historical_prices;

CREATE TABLE stock_data (
    id SERIAL PRIMARY KEY NOT NULL,
    bar_number INTEGER NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    interval VARCHAR(10) NOT NULL,
    open NUMERIC(15, 4) NOT NULL,
    high NUMERIC(15, 4) NOT NULL,
    low NUMERIC(15, 4) NOT NULL,
    close NUMERIC(15, 4) NOT NULL,
    is_relative BOOLEAN NOT NULL
);

CREATE TABLE timestamp_data (
    id SERIAL PRIMARY KEY,
    bar_number INTEGER NOT NULL,
    interval VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    UNIQUE (bar_number, interval)
);
