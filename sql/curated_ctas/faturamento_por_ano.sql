CREATE TABLE "lakehouse-curated".faturamento_por_ano
WITH (
    format = 'PARQUET', 
    parquet_compression = 'SNAPPY',
    external_location = 's3://pos-graduacao-lakehouse-km/curated/faturamento_por_ano/'
)
AS 
SELECT 
    substr(cast(dataemissao as varchar), 1, 4) AS ano, 
    sum(qtditens * valorunitario) AS faturamento
FROM "lakehouse-curated".trusted
GROUP BY substr(cast(dataemissao as varchar), 1, 4)


