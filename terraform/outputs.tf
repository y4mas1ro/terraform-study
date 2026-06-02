output "kinesis_stream_name" {
  value = aws_kinesis_stream.stock_stream.name
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.stock_prices.name
}

output "s3_bucket_name" {
  value = aws_s3_bucket.stock_archive.bucket
}
