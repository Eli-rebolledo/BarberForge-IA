# Ollama en Docker Desktop, fuera de Minikube (así el modelo de lenguaje no le quita RAM al clúster). Igual que en el
# Laboratorio 2: imagen + volumen + contenedor descritos con el proveedor de Docker.

resource "docker_image" "ollama" {
  count        = var.ollama_con_opentofu ? 1 : 0
  name         = var.ollama_imagen
  keep_locally = true
}

resource "docker_volume" "ollama" {
  count = var.ollama_con_opentofu ? 1 : 0
  name  = "barberforge-ollama-modelos"
}

resource "docker_network" "ollama" {
  count = var.ollama_con_opentofu ? 1 : 0
  name  = "barberforge-ia"
}

resource "docker_container" "ollama" {
  count   = var.ollama_con_opentofu ? 1 : 0
  name    = "barberforge-ollama"
  image   = docker_image.ollama[0].image_id
  restart = "unless-stopped"
  env     = ["OLLAMA_KEEP_ALIVE=30m"]

  ports {
    internal = 11434
    external = var.ollama_puerto
  }

  volumes {
    volume_name    = docker_volume.ollama[0].name
    container_path = "/root/.ollama"
  }

  networks_advanced {
    name = docker_network.ollama[0].name
  }
}

# Contenedor de una sola vez que descarga los modelos (la primera vez tarda varios minutos).
# Ver el progreso: docker logs -f barberforge-ollama-modelos
resource "docker_container" "ollama_modelos" {
  count      = var.ollama_con_opentofu ? 1 : 0
  name       = "barberforge-ollama-modelos"
  image      = docker_image.ollama[0].image_id
  must_run   = false
  restart    = "no"
  entrypoint = ["/bin/sh", "-c"]
  command    = ["sleep 3 && ollama pull ${var.modelo_embeddings} && ollama pull ${var.modelo_llm}"]
  env        = ["OLLAMA_HOST=http://barberforge-ollama:11434"]

  networks_advanced {
    name = docker_network.ollama[0].name
  }

  depends_on = [docker_container.ollama]
}
