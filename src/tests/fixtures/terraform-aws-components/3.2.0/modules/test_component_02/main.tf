resource "null_resource\" \"hello_world" {
  provisioner "local-exec" {
    command = "echo Hello, World!"
  }
}

resource "aws_s3_bucket" "my_bucket" {
  bucket = "my-bucket-name"
  acl = "private"
}