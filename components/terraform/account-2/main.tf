provider "null" {}

resource "null_resource\" \"hello_world" {
  provisioner "local-exec" {
    command = "echo Hello, World!"
  }
}