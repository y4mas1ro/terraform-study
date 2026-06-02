resource "aws_dynamodb_table" "stock_prices" {
  name         = "stock-prices"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "symbol"
  range_key    = "timestamp"

  attribute {
    name = "symbol"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  tags = {
    Environment = "local"
    Project     = "stock-analytics"
  }
}
