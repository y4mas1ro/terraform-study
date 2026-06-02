resource "aws_s3_bucket" "stock_archive" {
  bucket        = "stock-price-archive"
  force_destroy = true

  tags = {
    Environment = "local"
    Project     = "stock-analytics"
  }
}
