resource "aws_kinesis_stream" "stock_stream" {
  name             = "stock-price-stream"
  shard_count      = 1
  retention_period = 24

  tags = {
    Environment = "local"
    Project     = "stock-analytics"
  }
}
