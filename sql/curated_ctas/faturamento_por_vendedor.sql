CREATE TABLE "lakehouse-curated".faturamento_por_vendedor
WITH (
    format = 'PARQUET', 
    parquet_compression = 'SNAPPY',
    external_location = 's3://pos-graduacao-lakehouse-km/curated/faturamento_por_vendedor/'
)
AS 
SELECT 
    vendedor, 
    sum(qtditens * valorunitario) AS faturamento
FROM "lakehouse-curated".trusted 
GROUP BY vendedor;
