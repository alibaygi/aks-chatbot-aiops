terraform {
  required_version = ">= 1.7"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.110"
    }
  }

  # ── Remote state (uncomment after running the storage setup in the README) ────
  # backend "azurerm" {
  #   resource_group_name  = "rg-chatbot-tfstate"
  #   storage_account_name = "chatbottfstate2026ali"
  #   container_name       = "tfstate"
  #   key                  = "chatbot.tfstate"
  # }
}

provider "azurerm" {
  features {
    resource_group {
      # AKS auto-provisions resources (e.g. ContainerInsights solution) that
      # Terraform doesn't manage. Without this flag, terraform destroy fails
      # if any such resources remain in the group at deletion time.
      prevent_deletion_if_contains_resources = false
    }
  }
}

# ── Resource Group ─────────────────────────────────────────────────────────────
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

# ── Azure Container Registry ───────────────────────────────────────────────────
resource "azurerm_container_registry" "main" {
  name                = var.acr_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = var.acr_sku
  admin_enabled       = false
  tags                = var.tags
}

# ── AKS Cluster ────────────────────────────────────────────────────────────────
resource "azurerm_kubernetes_cluster" "main" {
  name                = var.aks_cluster_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  dns_prefix          = var.aks_cluster_name
  kubernetes_version  = var.kubernetes_version

  default_node_pool {
    name       = "nodepool1"
    node_count = var.node_count
    vm_size    = var.node_vm_size
  }

  # System-assigned managed identity — no service principal secrets to rotate.
  identity {
    type = "SystemAssigned"
  }

  # Ship control-plane logs to Azure Monitor (free tier).
  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  }

  tags = var.tags
}

# ── Log Analytics Workspace (for AKS diagnostics) ─────────────────────────────
resource "azurerm_log_analytics_workspace" "main" {
  name                = "${var.aks_cluster_name}-logs"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = var.tags
}

# ── Grant AKS kubelet identity AcrPull on the registry ────────────────────────
# This lets every node pull images without storing registry credentials.
resource "azurerm_role_assignment" "aks_acr_pull" {
  principal_id                     = azurerm_kubernetes_cluster.main.kubelet_identity[0].object_id
  role_definition_name             = "AcrPull"
  scope                            = azurerm_container_registry.main.id
  skip_service_principal_aad_check = true
}
